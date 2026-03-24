"""
TriggerRouteGenerator: Dynamically generates FastAPI routes for state machine triggers.

This module reads state machine definitions and creates dedicated API endpoints
for each trigger defined in the Mermaid diagrams. For route stability across
version history, routes are generated from all versions of each active workflow
name (union of triggers per state machine name).

URL Pattern: POST /api/{sm_name}/{instance_id}/{trigger}
"""
import logging
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import StateMachineDefinition
from app.engine import MermaidParser, Transition

logger = logging.getLogger(__name__)


@dataclass
class TriggerRoute:
    """Represents a generated trigger route."""
    state_machine_name: str
    trigger_name: str
    from_states: List[str]
    to_state: str
    definition_id: int
    payload_schema: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)
    guards: List[str] = field(default_factory=list)
    is_actionless: bool = False


class TriggerRouteGenerator:
    """
    Generates FastAPI routes dynamically from state machine definitions.
    
    On startup, reads definitions for active workflow names, parses Mermaid
    diagrams across versions, and creates one stable route per trigger.
    """
    
    def __init__(self):
        self.router = APIRouter(prefix="/api")
        self.routes: Dict[str, Dict[str, TriggerRoute]] = {}  # {sm_name: {trigger: TriggerRoute}}
        self._route_handlers: Dict[str, Callable] = {}
    
    def generate_routes(self, session: Session) -> APIRouter:
        """
        Generate all trigger routes from definitions of active workflow names.
        
        Args:
            session: Database session
            
        Returns:
            FastAPI APIRouter with all generated routes
        """
        logger.info("Generating trigger routes from state machine definitions...")
        
        # Query all definitions so routes stay stable across version history
        statement = select(StateMachineDefinition).order_by(
            StateMachineDefinition.name,
            StateMachineDefinition.version.desc()
        )
        definitions = session.exec(statement).all()

        # Only expose workflows that currently have an active version
        active_workflow_names = {definition.name for definition in definitions if definition.is_active}
        filtered_definitions = [
            definition for definition in definitions
            if definition.name in active_workflow_names
        ]

        logger.info(
            "Found %s definitions across %s active workflow(s)",
            len(filtered_definitions),
            len(active_workflow_names)
        )

        definitions_by_name: Dict[str, List[StateMachineDefinition]] = {}
        for definition in filtered_definitions:
            definitions_by_name.setdefault(definition.name, []).append(definition)

        for sm_name, sm_definitions in definitions_by_name.items():
            self._generate_routes_for_state_machine(sm_name, sm_definitions)
        
        total_routes = sum(len(triggers) for triggers in self.routes.values())
        logger.info(f"Generated {total_routes} trigger routes for {len(self.routes)} state machines")
        
        return self.router
    
    def _generate_routes_for_state_machine(
        self,
        sm_name: str,
        definitions: List[StateMachineDefinition]
    ) -> None:
        """
        Generate stable trigger routes for a state machine across versions.
        
        Args:
            sm_name: State machine name
            definitions: All versions for this state machine name
        """
        self.routes[sm_name] = {}

        active_definition = next(
            (
                definition
                for definition in sorted(definitions, key=lambda d: d.version, reverse=True)
                if definition.is_active
            ),
            None
        )

        # Group transitions by trigger name across all versions
        trigger_transitions: Dict[str, List[Tuple[StateMachineDefinition, Transition]]] = {}
        for definition in definitions:
            try:
                parser = MermaidParser(definition.mermaid_definition)
            except Exception as e:
                logger.error(f"Failed to parse Mermaid for '{definition.name}' v{definition.version}: {e}")
                continue

            for transition in parser.transitions:
                if transition.trigger_name:
                    trigger_transitions.setdefault(transition.trigger_name, []).append((definition, transition))

        # Create one route per unique trigger name
        for trigger_name, transition_candidates in trigger_transitions.items():
            from_states = sorted({transition.source for _, transition in transition_candidates})

            preferred_definition, preferred_transition = self._select_preferred_candidate(
                transition_candidates, active_definition
            )

            trigger_route = TriggerRoute(
                state_machine_name=sm_name,
                trigger_name=trigger_name,
                from_states=from_states,
                to_state=preferred_transition.target,
                definition_id=preferred_definition.id,
                actions=preferred_transition.actions,
                guards=preferred_transition.guards,
                is_actionless=preferred_transition.is_actionless
            )
            
            self.routes[sm_name][trigger_name] = trigger_route
            
            # Register the route with FastAPI
            self._register_route(trigger_route)
        
        logger.info(
            "Generated %s stable routes for '%s' across %s version(s)",
            len(trigger_transitions),
            sm_name,
            len(definitions)
        )

    def _select_preferred_candidate(
        self,
        transition_candidates: List[Tuple[StateMachineDefinition, Transition]],
        active_definition: Optional[StateMachineDefinition]
    ) -> Tuple[StateMachineDefinition, Transition]:
        """
        Select preferred transition metadata for docs/examples.

        Preference order:
        1) Active definition
        2) Highest version available
        """
        if active_definition:
            for definition, transition in transition_candidates:
                if definition.id == active_definition.id:
                    return definition, transition

        return max(transition_candidates, key=lambda candidate: candidate[0].version)
    
    def _register_route(self, trigger_route: TriggerRoute) -> None:
        """
        Register a FastAPI route for a trigger.
        
        Creates one endpoint:
        - POST /api/{sm_name}/{instance_id}/{trigger} - lookup by internal ID
        """
        sm_name = trigger_route.state_machine_name
        trigger_name = trigger_route.trigger_name
        
        # Route by instance ID
        path_by_id = f"/{sm_name}/{{instance_id}}/{trigger_name}"
        
        # Create handler function with closure over trigger_route
        async def trigger_handler_by_id(
            instance_id: int,
            request: Request,
            session: Session = Depends(get_session)
        ):
            return await self._execute_trigger(
                instance_id=instance_id,
                request=request,
                session=session,
                trigger_route=trigger_route
            )
        
        # Set unique function name for FastAPI
        trigger_handler_by_id.__name__ = f"trigger_{sm_name}_{trigger_name}_by_id"
        
        # Build OpenAPI response model description
        response_desc = {
            200: {
                "description": "Transition executed successfully",
                "content": {
                    "application/json": {
                        "example": {
                            "success": True,
                            "instance_id": 1,
                            "previous_state": trigger_route.from_states[0] if trigger_route.from_states else "STATE",
                            "new_state": trigger_route.to_state,
                            "trigger_name": trigger_name,
                            "execution_mode": "sync",
                            "version": 2
                        }
                    }
                }
            },
            400: {"description": "Invalid transition or guard failed"},
            404: {"description": "Instance not found"},
            422: {"description": "Payload validation failed"}
        }
        
        self.router.add_api_route(
            path_by_id,
            trigger_handler_by_id,
            methods=["POST"],
            summary=f"Trigger {trigger_name} on {sm_name}",
            description=f"Trigger '{trigger_name}' transition on a {sm_name} instance.\n\n**Valid from states:** {', '.join(trigger_route.from_states)}\n\n**Target state:** {trigger_route.to_state}",
            response_class=JSONResponse,
            tags=[sm_name],
            responses=response_desc
        )
        
        logger.debug(f"Registered route: {path_by_id}")
    
    async def _execute_trigger(
        self,
        instance_id: Optional[int],
        request: Request,
        session: Session,
        trigger_route: TriggerRoute
    ) -> JSONResponse:
        """
        Execute a trigger on a state machine instance.
        
        This is a placeholder that will be replaced by TriggerExecutionEngine.
        
        Args:
            instance_id: Internal instance ID
            request: FastAPI request object
            session: Database session
            trigger_route: The trigger route configuration
            
        Returns:
            JSON response with transition result
        """
        from app.trigger_engine import TriggerExecutionEngine
        
        # Parse request body
        try:
            payload = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        except Exception:
            payload = {}
        
        # Extract tracing headers stashed by CorrelationIdMiddleware
        correlation_id = getattr(request.state, "correlation_id", None)
        idempotency_key = getattr(request.state, "idempotency_key", None)
        
        # Create execution engine and execute
        exec_engine = TriggerExecutionEngine(session)
        
        result = await exec_engine.execute(
            state_machine_name=trigger_route.state_machine_name,
            trigger_name=trigger_route.trigger_name,
            instance_id=instance_id,
            payload=payload,
            trigger_route=trigger_route,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )
        
        # Map error_code to proper HTTP status
        from app.trigger_engine import ErrorCode
        if result.get("success", False):
            status_code = 200
        else:
            error_code = result.get("error_code", "")
            status_code = ErrorCode.HTTP_STATUS.get(error_code, 400)
        
        return JSONResponse(content=result, status_code=status_code)
    
    def get_routes_for_state_machine(self, sm_name: str) -> Dict[str, TriggerRoute]:
        """Get all trigger routes for a state machine."""
        return self.routes.get(sm_name, {})
    
    def get_all_routes(self) -> Dict[str, Dict[str, TriggerRoute]]:
        """Get all registered trigger routes."""
        return self.routes


# Global instance for route generation
_trigger_router_generator: Optional[TriggerRouteGenerator] = None


def get_trigger_router(session: Session) -> APIRouter:
    """
    Get or create the trigger router with all dynamic routes.
    
    This should be called once during application startup.
    """
    global _trigger_router_generator
    
    if _trigger_router_generator is None:
        _trigger_router_generator = TriggerRouteGenerator()
        _trigger_router_generator.generate_routes(session)
    
    return _trigger_router_generator.router


def reload_trigger_routes(session: Session) -> APIRouter:
    """
    Reload all trigger routes (e.g., after definition changes).
    
    Note: In production, this may require application restart
    as FastAPI doesn't support dynamic route removal.
    """
    global _trigger_router_generator
    
    _trigger_router_generator = TriggerRouteGenerator()
    _trigger_router_generator.generate_routes(session)
    
    logger.info("Trigger routes reloaded")
    return _trigger_router_generator.router
