from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import logging

from app.database import get_session
from app.models import StateMachineDefinition, WorkflowRelation
from app.engine import MermaidParser
from app.services.transition_metadata_service import populate_transition_metadata

router = APIRouter(prefix="/api/state-machines", tags=["state-machines"])
logger = logging.getLogger(__name__)


class CreateStateMachineDefinitionRequest(BaseModel):
    name: str
    mermaid_definition: str
    initial_state: Optional[str] = None
    description: Optional[str] = None


class CreateVersionRequest(BaseModel):
    mermaid_definition: str
    initial_state: Optional[str] = None
    description: Optional[str] = None
    change_log: str


class StateMachineDefinitionResponse(BaseModel):
    id: int
    name: str
    version: int
    initial_state: str
    is_active: bool
    description: Optional[str]
    change_log: Optional[str] = None
    created_by: str = "system"
    created_at: str


class StateMachineDefinitionDetailResponse(StateMachineDefinitionResponse):
    mermaid_definition: str


def _definition_response(w: StateMachineDefinition) -> StateMachineDefinitionResponse:
    return StateMachineDefinitionResponse(
        id=w.id,
        name=w.name,
        version=w.version,
        initial_state=w.initial_state,
        is_active=w.is_active,
        description=w.description,
        change_log=w.change_log,
        created_by=w.created_by,
        created_at=w.created_at.isoformat()
    )


def _definition_detail_response(w: StateMachineDefinition) -> StateMachineDefinitionDetailResponse:
    return StateMachineDefinitionDetailResponse(
        id=w.id,
        name=w.name,
        version=w.version,
        initial_state=w.initial_state,
        is_active=w.is_active,
        description=w.description,
        change_log=w.change_log,
        created_by=w.created_by,
        mermaid_definition=w.mermaid_definition,
        created_at=w.created_at.isoformat()
    )


def _validate_and_parse_mermaid(mermaid_definition: str) -> MermaidParser:
    """Validate Mermaid syntax and return parser. Raises HTTPException on failure."""
    try:
        parser = MermaidParser(mermaid_definition)
        errors = parser.validate()
        if errors:
            raise HTTPException(status_code=400, detail=f"Invalid Mermaid diagram: {'; '.join(errors)}")
        return parser
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Mermaid diagram: {str(e)}")


@router.post("/definitions", response_model=StateMachineDefinitionResponse)
def create_workflow_definition(
    request: CreateStateMachineDefinitionRequest,
    session: Session = Depends(get_session)
):
    """Create a new workflow definition."""
    parser = _validate_and_parse_mermaid(request.mermaid_definition)
    
    initial_state = request.initial_state or parser.initial_state
    if not initial_state:
        raise HTTPException(
            status_code=400,
            detail="Initial state must be provided or defined in the Mermaid diagram ([*] --> State)"
        )
    
    existing = session.exec(
        select(StateMachineDefinition).where(StateMachineDefinition.name == request.name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Workflow '{request.name}' already exists")
    
    workflow = StateMachineDefinition(
        name=request.name,
        mermaid_definition=request.mermaid_definition,
        initial_state=initial_state,
        description=request.description,
        version=1,
        is_active=True,
        created_by="api"
    )
    
    session.add(workflow)
    session.commit()
    session.refresh(workflow)
    
    try:
        populate_transition_metadata(session, workflow)
    except Exception as e:
        logger.warning(f"Failed to populate transition metadata for '{workflow.name}': {e}")
    
    return _definition_response(workflow)


@router.get("/definitions", response_model=List[StateMachineDefinitionResponse])
def list_workflow_definitions(
    active_only: bool = True,
    session: Session = Depends(get_session)
):
    """List workflow definitions. By default returns only active versions."""
    statement = select(StateMachineDefinition)
    if active_only:
        statement = statement.where(StateMachineDefinition.is_active)
    statement = statement.order_by(
        StateMachineDefinition.name,
        StateMachineDefinition.version.desc()
    )
    
    workflows = session.exec(statement).all()
    return [_definition_response(w) for w in workflows]


@router.get("/definitions/{definition_id}", response_model=StateMachineDefinitionDetailResponse)
def get_workflow_definition(
    definition_id: int,
    session: Session = Depends(get_session)
):
    """Get full details of a workflow definition."""
    workflow = session.get(StateMachineDefinition, definition_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    
    return _definition_detail_response(workflow)


@router.get(
    "/definitions/{definition_id}/versions",
    response_model=List[StateMachineDefinitionResponse]
)
def list_definition_versions(
    definition_id: int,
    session: Session = Depends(get_session)
):
    """List all versions of a workflow definition."""
    workflow = session.get(StateMachineDefinition, definition_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    
    statement = select(StateMachineDefinition).where(
        StateMachineDefinition.name == workflow.name
    ).order_by(StateMachineDefinition.version.desc())
    
    versions = session.exec(statement).all()
    return [_definition_response(v) for v in versions]


@router.post(
    "/definitions/{definition_id}/versions",
    response_model=StateMachineDefinitionResponse
)
def create_definition_version(
    definition_id: int,
    request: CreateVersionRequest,
    session: Session = Depends(get_session)
):
    """Create a new version of a workflow definition.
    
    Deactivates the current active version and creates a new one.
    """
    old_workflow = session.get(StateMachineDefinition, definition_id)
    if not old_workflow:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    
    parser = _validate_and_parse_mermaid(request.mermaid_definition)
    
    initial_state = request.initial_state or parser.initial_state or old_workflow.initial_state
    if not initial_state:
        raise HTTPException(
            status_code=400,
            detail="Initial state must be provided or defined in the Mermaid diagram"
        )
    
    # Deactivate old version
    old_workflow.is_active = False
    old_workflow.updated_at = datetime.now(timezone.utc)
    
    # Find the highest version number for this workflow name
    max_version_stmt = select(StateMachineDefinition.version).where(
        StateMachineDefinition.name == old_workflow.name
    ).order_by(StateMachineDefinition.version.desc())
    max_version = session.exec(max_version_stmt).first() or 0
    
    new_workflow = StateMachineDefinition(
        name=old_workflow.name,
        description=request.description if request.description is not None else old_workflow.description,
        initial_state=initial_state,
        mermaid_definition=request.mermaid_definition,
        version=max_version + 1,
        is_active=True,
        parent_version_id=old_workflow.id,
        change_log=request.change_log,
        created_by="api"
    )
    
    session.add(old_workflow)
    session.add(new_workflow)
    session.commit()
    session.refresh(new_workflow)
    
    try:
        populate_transition_metadata(session, new_workflow)
    except Exception as e:
        logger.warning(f"Failed to populate transition metadata for '{new_workflow.name}' v{new_workflow.version}: {e}")
    
    return _definition_response(new_workflow)


@router.post(
    "/definitions/{definition_id}/activate",
    response_model=StateMachineDefinitionResponse
)
def activate_definition_version(
    definition_id: int,
    session: Session = Depends(get_session)
):
    """Activate a specific workflow version (deactivates all other versions of the same workflow)."""
    workflow = session.get(StateMachineDefinition, definition_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    
    all_versions = session.exec(
        select(StateMachineDefinition).where(
            StateMachineDefinition.name == workflow.name
        )
    ).all()
    
    for v in all_versions:
        v.is_active = (v.id == definition_id)
        v.updated_at = datetime.now(timezone.utc)
        session.add(v)
    
    session.commit()
    session.refresh(workflow)
    
    return _definition_response(workflow)


# --- Workflow Relation endpoints ---


class WorkflowRelationRequest(BaseModel):
    child_workflow: str
    parent_workflow: str
    context_key: str
    parent_id_type: str = "number"
    created_from_state: Optional[str] = None
    context_mapping: Optional[dict] = None


class WorkflowRelationResponse(BaseModel):
    id: int
    child_workflow: str
    parent_workflow: str
    context_key: str
    parent_id_type: str
    created_from_state: Optional[str]
    context_mapping: Optional[dict]


def _relation_response(r: WorkflowRelation) -> WorkflowRelationResponse:
    import json as _json
    ctx_map = None
    if r.context_mapping:
        try:
            ctx_map = _json.loads(r.context_mapping) if isinstance(r.context_mapping, str) else r.context_mapping
        except Exception:
            ctx_map = None
    return WorkflowRelationResponse(
        id=r.id,
        child_workflow=r.child_workflow,
        parent_workflow=r.parent_workflow,
        context_key=r.context_key,
        parent_id_type=r.parent_id_type,
        created_from_state=r.created_from_state,
        context_mapping=ctx_map
    )


@router.get("/relations", response_model=List[WorkflowRelationResponse])
def list_workflow_relations(
    workflow_name: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """List workflow relationships.
    
    Optionally filter by workflow name (matches either parent or child).
    The frontend uses this to replace client-side workflowRelations config.
    """
    statement = select(WorkflowRelation)
    if workflow_name:
        statement = statement.where(
            (WorkflowRelation.parent_workflow == workflow_name) |
            (WorkflowRelation.child_workflow == workflow_name)
        )
    
    relations = session.exec(statement).all()
    return [_relation_response(r) for r in relations]


@router.post("/relations", response_model=WorkflowRelationResponse, status_code=201)
def create_workflow_relation(
    request: WorkflowRelationRequest,
    session: Session = Depends(get_session)
):
    """Create a workflow relationship (links_to / created_from)."""
    import json as _json
    
    relation = WorkflowRelation(
        child_workflow=request.child_workflow,
        parent_workflow=request.parent_workflow,
        context_key=request.context_key,
        parent_id_type=request.parent_id_type,
        created_from_state=request.created_from_state,
        context_mapping=_json.dumps(request.context_mapping) if request.context_mapping else None
    )
    session.add(relation)
    session.commit()
    session.refresh(relation)
    
    return _relation_response(relation)


@router.delete("/relations/{relation_id}", status_code=204)
def delete_workflow_relation(
    relation_id: int,
    session: Session = Depends(get_session)
):
    """Delete a workflow relationship."""
    relation = session.get(WorkflowRelation, relation_id)
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")
    
    session.delete(relation)
    session.commit()
