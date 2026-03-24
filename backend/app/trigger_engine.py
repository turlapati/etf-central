"""
TriggerExecutionEngine: Orchestrates the full trigger execution lifecycle.

Responsibilities:
1. Validate instance exists and is in valid state
2. Validate payload against schema
3. Evaluate guards (if any)
4. Execute actions (sync or async based on timeout)
5. Perform state transition
6. Persist all changes to database
"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import (
    StateMachineDefinition,
    StateMachineInstance,
    StateMachineTransitionLog,
    TransitionMetadata,
    TransitionAction,
    ActionDefinition
)
from app.engine import StateMachine
from app.registry import get_action_function
from app.schemas.trigger_schemas import PayloadValidator
from app.guards import evaluate_guards
from app.services.async_task_service import AsyncTaskQueue

logger = logging.getLogger(__name__)


class ErrorCode:
    """Structured error codes that map to HTTP statuses."""
    NOT_FOUND = "not_found"                # 404
    WORKFLOW_MISMATCH = "workflow_mismatch" # 409
    INVALID_TRANSITION = "invalid_transition" # 409
    GUARD_FAILED = "guard_failed"          # 409
    PAYLOAD_VALIDATION = "payload_validation" # 422
    ACTION_FAILED = "action_failed"        # 500
    INTERNAL = "internal_error"            # 500

    HTTP_STATUS = {
        NOT_FOUND: 404,
        WORKFLOW_MISMATCH: 409,
        INVALID_TRANSITION: 409,
        GUARD_FAILED: 409,
        PAYLOAD_VALIDATION: 422,
        ACTION_FAILED: 500,
        INTERNAL: 500,
    }


@dataclass
class ExecutionResult:
    """Result of a trigger execution."""
    success: bool
    instance_id: int
    previous_state: str
    new_state: str
    trigger_name: str
    execution_mode: str  # "sync" or "async"
    job_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    action_results: Optional[List[Dict[str, Any]]] = None
    version: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "success": self.success,
            "instance_id": self.instance_id,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "trigger_name": self.trigger_name,
            "execution_mode": self.execution_mode,
            "version": self.version
        }
        if self.job_id:
            result["job_id"] = self.job_id
        if self.error:
            result["error"] = self.error
        if self.error_code:
            result["error_code"] = self.error_code
        if self.action_results:
            result["action_results"] = self.action_results
        return result
    
    @property
    def http_status(self) -> int:
        if self.success:
            return 200
        return ErrorCode.HTTP_STATUS.get(self.error_code or "", 400)


class TriggerExecutionEngine:
    """
    Executes state machine triggers with full validation and action execution.
    """
    
    SYNC_TIMEOUT_THRESHOLD = 30  # Actions with timeout <= this run synchronously
    
    def __init__(self, session: Session):
        self.session = session
    
    async def execute(
        self,
        state_machine_name: str,
        trigger_name: str,
        instance_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
        trigger_route: Optional[Any] = None,
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a trigger on a state machine instance.
        
        Args:
            state_machine_name: Name of the state machine
            trigger_name: Name of the trigger to execute
            instance_id: Internal instance ID
            payload: Trigger payload data
            trigger_route: TriggerRoute configuration (optional, for optimization)
            correlation_id: End-to-end trace id from X-Correlation-Id header
            idempotency_key: Client-provided dedup key from Idempotency-Key header
            
        Returns:
            Dictionary with execution result
        """
        payload = payload or {}
        
        try:
            # Step 1: Load instance
            instance = self._load_instance(instance_id)
            if not instance:
                return ExecutionResult(
                    success=False,
                    instance_id=instance_id or 0,
                    previous_state="",
                    new_state="",
                    trigger_name=trigger_name,
                    execution_mode="sync",
                    error=f"Instance not found: id={instance_id}",
                    error_code=ErrorCode.NOT_FOUND
                ).to_dict()
            
            # Step 2: Load definition
            definition = self.session.get(StateMachineDefinition, instance.definition_id)
            if not definition:
                return ExecutionResult(
                    success=False,
                    instance_id=instance.id,
                    previous_state=instance.current_state,
                    new_state=instance.current_state,
                    trigger_name=trigger_name,
                    execution_mode="sync",
                    error="State machine definition not found",
                    error_code=ErrorCode.NOT_FOUND
                ).to_dict()
            
            # Step 2.5: Verify URL workflow matches instance's definition
            if state_machine_name and definition.name != state_machine_name:
                return ExecutionResult(
                    success=False,
                    instance_id=instance.id,
                    previous_state=instance.current_state,
                    new_state=instance.current_state,
                    trigger_name=trigger_name,
                    execution_mode="sync",
                    error=f"Instance {instance.id} belongs to workflow '{definition.name}', not '{state_machine_name}'",
                    error_code=ErrorCode.WORKFLOW_MISMATCH
                ).to_dict()
            
            # Step 3: Validate transition
            machine = StateMachine(definition.mermaid_definition, instance.current_state)
            next_state = machine.get_next_state(trigger_name)
            
            if next_state is None:
                available = machine.get_available_triggers()
                return ExecutionResult(
                    success=False,
                    instance_id=instance.id,
                    previous_state=instance.current_state,
                    new_state=instance.current_state,
                    trigger_name=trigger_name,
                    execution_mode="sync",
                    error=f"Invalid transition: Cannot trigger '{trigger_name}' from state '{instance.current_state}'. Available: {available}",
                    error_code=ErrorCode.INVALID_TRANSITION
                ).to_dict()
            
            # Step 4: Load transition metadata (for guards, actions, payload schema)
            transition_meta = self._load_transition_metadata(
                definition.id, instance.current_state, trigger_name
            )
            
            # Step 4.5: Get transition from Mermaid for payload schema
            transition = machine.get_transition(trigger_name)
            mermaid_schema = transition.payload_schema if transition else {}
            
            # Step 5: Validate payload against schema
            db_schema = {}
            if transition_meta and transition_meta.payload_schema:
                try:
                    db_schema = json.loads(transition_meta.payload_schema) if isinstance(transition_meta.payload_schema, str) else transition_meta.payload_schema
                except json.JSONDecodeError:
                    db_schema = {}
            
            # Get action schemas for inference fallback
            action_schemas = self._get_action_schemas(transition_meta) if transition_meta else []
            
            validator = PayloadValidator(
                mermaid_schema=mermaid_schema,
                db_schema=db_schema,
                action_schemas=action_schemas
            )
            
            if validator.has_schema():
                validation_result = validator.validate(payload)
                if not validation_result["valid"]:
                    error_details = "; ".join(
                        f"{e['field']}: {e['message']}" for e in validation_result["errors"]
                    )
                    return ExecutionResult(
                        success=False,
                        instance_id=instance.id,
                        previous_state=instance.current_state,
                        new_state=instance.current_state,
                        trigger_name=trigger_name,
                        execution_mode="sync",
                        error=f"Payload validation failed: {error_details}",
                        error_code=ErrorCode.PAYLOAD_VALIDATION
                    ).to_dict()
                # Use validated/coerced payload
                payload = validation_result["data"]
            
            # Step 6: Evaluate guards
            if transition_meta and transition_meta.guard_expression:
                guard_result = self._evaluate_guard(
                    transition_meta.guard_expression,
                    instance.get_context(),
                    payload
                )
                if not guard_result["passed"]:
                    return ExecutionResult(
                        success=False,
                        instance_id=instance.id,
                        previous_state=instance.current_state,
                        new_state=instance.current_state,
                        trigger_name=trigger_name,
                        execution_mode="sync",
                        error=f"Guard failed: {guard_result['reason']}",
                        error_code=ErrorCode.GUARD_FAILED
                    ).to_dict()
            
            # Step 6: Perform state transition first
            previous_state = instance.current_state
            instance.current_state = next_state
            instance.version += 1
            instance.updated_at = datetime.now(timezone.utc)
            
            # Merge payload into context
            if payload:
                instance.update_context(payload)
            
            # Step 7: Create transition log (needed for TaskExecution FK)
            log = StateMachineTransitionLog(
                instance_id=instance.id,
                from_state=previous_state,
                to_state=next_state,
                trigger_name=trigger_name,
                trigger_type="api",
                context_snapshot=instance.context,
                triggered_by="api",
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
            )
            
            self.session.add(instance)
            self.session.add(log)
            self.session.commit()
            self.session.refresh(log)  # Get the log ID for async actions
            
            # Step 8: Execute actions (now we have transition_log_id)
            action_results = []
            has_async = False
            if transition_meta:
                action_results, has_async = await self._execute_actions(
                    transition_meta,
                    instance,
                    payload,
                    log.id
                )
            
            # Merge sync action results into context
            for result in action_results:
                if result.get("success") and result.get("data") and result.get("execution_mode") != "async":
                    instance.update_context(result["data"])
            
            # Step 9: Check for terminal state
            machine_new = StateMachine(definition.mermaid_definition, next_state)
            if machine_new.is_terminal_state():
                context = instance.get_context()
                instance.status = context.get("status", "completed")
            
            # Step 10: Persist context updates
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            
            logger.info(f"Trigger executed: {state_machine_name}/{instance.id}/{trigger_name}: {previous_state} -> {next_state}")
            
            return ExecutionResult(
                success=True,
                instance_id=instance.id,
                previous_state=previous_state,
                new_state=next_state,
                trigger_name=trigger_name,
                execution_mode="async" if has_async else "sync",
                action_results=action_results if action_results else None,
                version=instance.version
            ).to_dict()
            
        except Exception as e:
            logger.error(f"Trigger execution failed: {e}")
            return ExecutionResult(
                success=False,
                instance_id=instance_id or 0,
                previous_state="",
                new_state="",
                trigger_name=trigger_name,
                execution_mode="sync",
                error=str(e),
                error_code=ErrorCode.INTERNAL
            ).to_dict()
    
    def _load_instance(
        self,
        instance_id: Optional[int]
    ) -> Optional[StateMachineInstance]:
        """Load instance by ID."""
        if instance_id:
            return self.session.get(StateMachineInstance, instance_id)
        return None
    
    def _load_transition_metadata(
        self,
        definition_id: int,
        from_state: str,
        trigger_name: str
    ) -> Optional[TransitionMetadata]:
        """Load transition metadata for guard/action configuration."""
        statement = select(TransitionMetadata).where(
            TransitionMetadata.state_machine_definition_id == definition_id,
            TransitionMetadata.from_state == from_state,
            TransitionMetadata.trigger_name == trigger_name
        )
        return self.session.exec(statement).first()
    
    def _get_action_schemas(
        self,
        transition_meta: TransitionMetadata
    ) -> List[Dict[str, Any]]:
        """
        Get parameter schemas from actions associated with a transition.
        
        Used for payload schema inference when no explicit schema is defined.
        """
        schemas = []
        
        statement = select(TransitionAction, ActionDefinition).join(
            ActionDefinition,
            TransitionAction.action_definition_id == ActionDefinition.id
        ).where(
            TransitionAction.transition_metadata_id == transition_meta.id
        )
        
        action_rows = self.session.exec(statement).all()
        
        for _, action_def in action_rows:
            if action_def.parameters_schema:
                try:
                    schema = json.loads(action_def.parameters_schema) if isinstance(action_def.parameters_schema, str) else action_def.parameters_schema
                    schemas.append(schema)
                except json.JSONDecodeError:
                    pass
        
        return schemas
    
    def _evaluate_guard(
        self,
        guard_expression: str,
        context: Dict[str, Any],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a guard expression against context and payload.
        
        Uses the SafeGuardEvaluator for secure expression evaluation.
        Supports:
        - Simple comparisons: context.amount > 0
        - Compound conditions: context.status == "active" and payload.amount > 0
        - Membership: context.role in ["admin", "manager"]
        - Null checks: context.user is not None
        
        Returns:
            Dict with 'passed' (bool) and 'reason' (str if failed)
        """
        result = evaluate_guards(guard_expression, context, payload)
        return result.to_dict()
    
    async def _execute_actions(
        self,
        transition_meta: TransitionMetadata,
        instance: StateMachineInstance,
        payload: Dict[str, Any],
        transition_log_id: int
    ) -> tuple[List[Dict[str, Any]], bool]:
        """
        Execute actions associated with a transition.
        
        Args:
            transition_meta: Transition metadata with action configuration
            instance: The state machine instance
            payload: Trigger payload
            transition_log_id: ID of the transition log (for TaskExecution FK)
            
        Returns:
            Tuple of (action results list, has_async flag)
        """
        results = []
        has_async = False
        
        # Load transition actions
        statement = select(TransitionAction, ActionDefinition).join(
            ActionDefinition,
            TransitionAction.action_definition_id == ActionDefinition.id
        ).where(
            TransitionAction.transition_metadata_id == transition_meta.id
        ).order_by(TransitionAction.execution_order)
        
        action_rows = self.session.exec(statement).all()
        
        for transition_action, action_def in action_rows:
            # Determine execution mode
            is_async = action_def.is_async or action_def.timeout_seconds > self.SYNC_TIMEOUT_THRESHOLD
            
            if is_async:
                has_async = True
                # Queue for async execution
                result = await self._queue_async_action(
                    transition_action, action_def, instance, payload, transition_log_id
                )
            else:
                # Execute synchronously
                result = await self._execute_action_sync(
                    transition_action, action_def, instance, payload
                )
            
            results.append(result)
            
            # Check if we should stop on error (only for sync actions)
            if not is_async and not result["success"] and not transition_action.continue_on_error:
                logger.error(f"Action {action_def.name} failed, stopping execution")
                break
        
        return results, has_async
    
    async def _execute_action_sync(
        self,
        transition_action: TransitionAction,
        action_def: ActionDefinition,
        instance: StateMachineInstance,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an action synchronously."""
        try:
            # Get the action function
            action_func = get_action_function(action_def.name)
            if not action_func:
                return {
                    "action": action_def.name,
                    "success": False,
                    "error": f"Action function not found: {action_def.name}"
                }
            
            # Build parameters from payload and context
            context = instance.get_context()
            param_mapping = json.loads(transition_action.parameter_mapping) if transition_action.parameter_mapping else {}
            
            # Build action parameters from context and payload
            action_params = {}
            if param_mapping:
                # Use explicit parameter mapping if provided
                for param_name, source in param_mapping.items():
                    if source.startswith("context."):
                        action_params[param_name] = context.get(source[8:])
                    elif source.startswith("payload."):
                        action_params[param_name] = payload.get(source[8:])
                    elif source in context:
                        action_params[param_name] = context.get(source)
                    elif source in payload:
                        action_params[param_name] = payload.get(source)
            else:
                # Default: pass parameters that the action function expects
                import inspect
                sig = inspect.signature(action_func)
                has_var_keyword = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in sig.parameters.values()
                )
                if has_var_keyword:
                    # Function accepts **kwargs — forward all payload keys
                    # (payload takes precedence over context for same-named keys)
                    for key, val in payload.items():
                        if key not in ('instance_id', 'context'):
                            action_params[key] = val
                else:
                    # Only pass explicitly declared parameters
                    for param_name, param in sig.parameters.items():
                        if param_name not in ['instance_id', 'context']:
                            if param_name in payload:
                                action_params[param_name] = payload[param_name]
                            elif param_name in context:
                                action_params[param_name] = context[param_name]
            
            # Execute the action
            result = action_func(
                instance_id=instance.id,
                context=context,
                **action_params
            )
            
            return {
                "action": action_def.name,
                "success": True,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Action {action_def.name} failed: {e}")
            return {
                "action": action_def.name,
                "success": False,
                "error": str(e)
            }
    
    async def _queue_async_action(
        self,
        transition_action: TransitionAction,
        action_def: ActionDefinition,
        instance: StateMachineInstance,
        payload: Dict[str, Any],
        transition_log_id: int
    ) -> Dict[str, Any]:
        """
        Queue an action for async execution.
        
        Creates a TaskExecution record and queues the action for background processing.
        """
        try:
            # Get parameter mapping
            param_mapping = json.loads(transition_action.parameter_mapping) if transition_action.parameter_mapping else {}
            
            # Queue the action
            queue = AsyncTaskQueue.get_instance()
            job_info = await queue.enqueue(
                transition_log_id=transition_log_id,
                action_def=action_def,
                instance=instance,
                payload=payload,
                parameter_mapping=param_mapping
            )
            
            logger.info(f"Queued async action: {action_def.name} (job_id={job_info.job_id})")
            
            return {
                "action": action_def.name,
                "success": True,
                "execution_mode": "async",
                "job_id": job_info.job_id,
                "task_execution_id": job_info.task_execution_id,
                "message": "Action queued for async execution"
            }
        except Exception as e:
            logger.error(f"Failed to queue async action {action_def.name}: {e}")
            return {
                "action": action_def.name,
                "success": False,
                "execution_mode": "async",
                "error": f"Failed to queue action: {e}"
            }
