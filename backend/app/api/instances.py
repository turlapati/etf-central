from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
import logging

from app.database import get_session
from app.models import StateMachineDefinition, StateMachineInstance, StateMachineTransitionLog
from app.engine import StateMachine
from app.services.async_task_service import get_task_execution_status, get_transition_task_executions

router = APIRouter(prefix="/api/state-machines", tags=["instances"])
logger = logging.getLogger(__name__)


class CreateInstanceRequest(BaseModel):
    workflow_name: Optional[str] = None
    definition_id: Optional[int] = None
    context: Dict[str, Any] = {}


class InstanceResponse(BaseModel):
    id: int
    definition_id: int
    workflow_name: str
    current_state: str
    status: str
    context: Dict[str, Any]
    version: int
    created_at: str
    updated_at: str
    available_events: Optional[List[str]] = None


class TriggerSchema(BaseModel):
    name: str
    payload_schema: Dict[str, Any] = {}


class InstanceDetailResponse(InstanceResponse):
    available_events: List[str]
    available_triggers: List[TriggerSchema] = []
    mermaid_definition: str


class TransitionLogResponse(BaseModel):
    id: int
    from_state: str
    to_state: str
    event: str
    triggered_by: Optional[str]
    context_snapshot: Dict[str, Any]
    error_message: Optional[str]
    created_at: str


@router.post("/instances", response_model=InstanceResponse)
def create_instance(
    request: CreateInstanceRequest,
    session: Session = Depends(get_session)
):
    """Create a new workflow instance."""
    
    # Get workflow definition
    if request.workflow_name:
        statement = select(StateMachineDefinition).where(
            StateMachineDefinition.name == request.workflow_name,
            StateMachineDefinition.is_active
        ).order_by(StateMachineDefinition.version.desc())
        definition = session.exec(statement).first()
        if not definition:
            raise HTTPException(
                status_code=404,
                detail=f"Active workflow '{request.workflow_name}' not found"
            )
    elif request.definition_id:
        definition = session.get(StateMachineDefinition, request.definition_id)
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
    else:
        raise HTTPException(status_code=400, detail="Must provide either workflow_name or definition_id")
    
    # Create instance
    instance = StateMachineInstance(
        definition_id=definition.id,
        current_state=definition.initial_state,
        status="active"
    )
    instance.set_context(request.context)
    
    session.add(instance)
    session.commit()
    session.refresh(instance)
    
    logger.info(f"Created workflow instance {instance.id} for workflow '{definition.name}'")
    
    return InstanceResponse(
        id=instance.id,
        definition_id=instance.definition_id,
        workflow_name=definition.name,
        current_state=instance.current_state,
        status=instance.status,
        context=instance.get_context(),
        version=instance.version,
        created_at=instance.created_at.isoformat(),
        updated_at=instance.updated_at.isoformat()
    )


@router.get("/instances", response_model=List[InstanceResponse])
def list_instances(
    workflow_name: Optional[str] = None,
    status: Optional[str] = None,
    current_state: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session)
):
    """List workflow instances with optional filters."""
    
    statement = select(StateMachineInstance, StateMachineDefinition).join(
        StateMachineDefinition,
        StateMachineInstance.definition_id == StateMachineDefinition.id
    )
    
    if workflow_name:
        statement = statement.where(StateMachineDefinition.name == workflow_name)
    
    if status:
        statement = statement.where(StateMachineInstance.status == status)
    
    if current_state:
        statement = statement.where(StateMachineInstance.current_state == current_state)
    
    statement = statement.order_by(StateMachineInstance.created_at.desc())
    statement = statement.offset(offset).limit(limit)
    
    results = session.exec(statement).all()
    
    # Get available events for each instance
    instances_with_events = []
    for instance, definition in results:
        machine = StateMachine(definition.mermaid_definition, instance.current_state)
        available_events = machine.get_available_triggers()
        
        instances_with_events.append(
            InstanceResponse(
                id=instance.id,
                definition_id=instance.definition_id,
                workflow_name=definition.name,
                current_state=instance.current_state,
                status=instance.status,
                context=instance.get_context(),
                version=instance.version,
                created_at=instance.created_at.isoformat(),
                updated_at=instance.updated_at.isoformat(),
                available_events=available_events
            )
        )
    
    return instances_with_events


@router.get("/instances/{instance_id}", response_model=InstanceDetailResponse)
def get_instance(
    instance_id: int,
    session: Session = Depends(get_session)
):
    """Get full details of a workflow instance."""
    
    instance = session.get(StateMachineInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    definition = session.get(StateMachineDefinition, instance.definition_id)
    
    # Get available events and trigger schemas
    machine = StateMachine(definition.mermaid_definition, instance.current_state)
    available_events = machine.get_available_triggers()
    triggers_with_schema = machine.get_available_triggers_with_schema()

    return InstanceDetailResponse(
        id=instance.id,
        definition_id=instance.definition_id,
        workflow_name=definition.name,
        current_state=instance.current_state,
        status=instance.status,
        context=instance.get_context(),
        version=instance.version,
        created_at=instance.created_at.isoformat(),
        updated_at=instance.updated_at.isoformat(),
        available_events=available_events,
        available_triggers=[
            TriggerSchema(name=t["name"], payload_schema=t["payload_schema"])
            for t in triggers_with_schema
        ],
        mermaid_definition=definition.mermaid_definition
    )


@router.get("/instances/{instance_id}/history", response_model=List[TransitionLogResponse])
def get_instance_history(
    instance_id: int,
    session: Session = Depends(get_session)
):
    """Get transition history for an instance."""
    
    # Verify instance exists
    instance = session.get(StateMachineInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # Get transition logs
    statement = select(StateMachineTransitionLog).where(
        StateMachineTransitionLog.instance_id == instance_id
    ).order_by(StateMachineTransitionLog.created_at)
    
    logs = session.exec(statement).all()
    
    return [
        TransitionLogResponse(
            id=log.id,
            from_state=log.from_state,
            to_state=log.to_state,
            event=log.trigger_name,
            triggered_by=log.triggered_by,
            context_snapshot=json.loads(log.context_snapshot) if log.context_snapshot else {},
            error_message=log.error_message,
            created_at=log.created_at.isoformat()
        )
        for log in logs
    ]


@router.get("/instances/{instance_id}/tasks")
def get_instance_tasks(
    instance_id: int,
    session: Session = Depends(get_session)
):
    """
    Get all task executions for an instance's transitions.
    
    Returns a list of all async tasks that have been executed for this instance.
    """
    # Verify instance exists
    instance = session.get(StateMachineInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # Get all transition logs for this instance
    log_stmt = select(StateMachineTransitionLog).where(
        StateMachineTransitionLog.instance_id == instance_id
    )
    logs = session.exec(log_stmt).all()
    
    all_tasks = []
    for log in logs:
        tasks = get_transition_task_executions(session, log.id)
        for task in tasks:
            task["transition_log_id"] = log.id
            task["from_state"] = log.from_state
            task["to_state"] = log.to_state
            task["trigger_name"] = log.trigger_name
        all_tasks.extend(tasks)
    
    return all_tasks


@router.get("/tasks/{task_id}")
def get_task_status(
    task_id: int,
    session: Session = Depends(get_session)
):
    """
    Get the status of a specific task execution.
    
    Use this to poll for async action completion.
    """
    status = get_task_execution_status(session, task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status


@router.get("/transitions/{transition_log_id}/tasks")
def get_transition_tasks(
    transition_log_id: int,
    session: Session = Depends(get_session)
):
    """
    Get all task executions for a specific transition.
    """
    # Verify transition log exists
    log = session.get(StateMachineTransitionLog, transition_log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Transition log not found")
    
    return get_transition_task_executions(session, transition_log_id)
