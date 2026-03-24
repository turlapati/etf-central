"""
Async Task Service: Background task queue for long-running actions.

Provides a simple in-process task queue for executing actions asynchronously.
For production, this could be replaced with Prefect, Celery, or similar.

Features:
- Queue actions for background execution
- Track task status in TaskExecution table
- Support for retries with exponential backoff
- Job status polling
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from sqlmodel import Session, select

from app.models import TaskExecution, ActionDefinition, StateMachineInstance
from app.registry import get_action_function
from app.database import get_engine

logger = logging.getLogger(__name__)


@dataclass
class AsyncJobInfo:
    """Information about a queued async job."""
    job_id: str
    task_execution_id: int
    action_name: str
    instance_id: int
    status: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "task_execution_id": self.task_execution_id,
            "action_name": self.action_name,
            "instance_id": self.instance_id,
            "status": self.status
        }


class AsyncTaskQueue:
    """
    Simple in-process async task queue.
    
    Uses asyncio and a thread pool for executing actions in the background.
    Tasks are tracked in the TaskExecution table.
    """
    
    _instance: Optional["AsyncTaskQueue"] = None
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pending_tasks: Dict[str, asyncio.Task] = {}
        self._running = True
    
    @classmethod
    def get_instance(cls) -> "AsyncTaskQueue":
        """Get or create the singleton queue instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def enqueue(
        self,
        transition_log_id: int,
        action_def: ActionDefinition,
        instance: StateMachineInstance,
        payload: Dict[str, Any],
        parameter_mapping: Dict[str, Any]
    ) -> AsyncJobInfo:
        """
        Queue an action for async execution.
        
        Args:
            transition_log_id: ID of the transition log entry
            action_def: Action definition to execute
            instance: State machine instance
            payload: Trigger payload
            parameter_mapping: Parameter mapping configuration
            
        Returns:
            AsyncJobInfo with job details
        """
        job_id = str(uuid.uuid4())
        
        # Create TaskExecution record
        engine = get_engine()
        with Session(engine) as session:
            task_execution = TaskExecution(
                transition_log_id=transition_log_id,
                action_definition_id=action_def.id,
                status="pending",
                created_at=datetime.now(timezone.utc)
            )
            session.add(task_execution)
            session.commit()
            session.refresh(task_execution)
            task_execution_id = task_execution.id
        
        # Create async task
        task = asyncio.create_task(
            self._execute_task(
                job_id=job_id,
                task_execution_id=task_execution_id,
                action_def_id=action_def.id,
                action_name=action_def.name,
                instance_id=instance.id,
                context=instance.get_context(),
                payload=payload,
                parameter_mapping=parameter_mapping,
                retry_policy=json.loads(action_def.retry_policy) if action_def.retry_policy else {}
            )
        )
        
        self.pending_tasks[job_id] = task
        
        logger.info(f"Queued async action: {action_def.name} (job_id={job_id})")
        
        return AsyncJobInfo(
            job_id=job_id,
            task_execution_id=task_execution_id,
            action_name=action_def.name,
            instance_id=instance.id,
            status="pending"
        )
    
    async def _execute_task(
        self,
        job_id: str,
        task_execution_id: int,
        action_def_id: int,
        action_name: str,
        instance_id: int,
        context: Dict[str, Any],
        payload: Dict[str, Any],
        parameter_mapping: Dict[str, Any],
        retry_policy: Dict[str, Any]
    ) -> None:
        """Execute a task with retry support."""
        max_attempts = retry_policy.get("max_attempts", 3)
        backoff = retry_policy.get("backoff", "exponential")
        
        engine = get_engine()
        
        # Update status to running
        with Session(engine) as session:
            task = session.get(TaskExecution, task_execution_id)
            if task:
                task.status = "running"
                task.started_at = datetime.now(timezone.utc)
                session.add(task)
                session.commit()
        
        attempt = 0
        last_error = None
        
        while attempt < max_attempts:
            attempt += 1
            
            try:
                # Get the action function
                action_func = get_action_function(action_name)
                if not action_func:
                    raise ValueError(f"Action function not found: {action_name}")
                
                # Build parameters
                action_params = {}
                if parameter_mapping:
                    # Use explicit parameter mapping if provided
                    for param_name, source in parameter_mapping.items():
                        if source.startswith("context."):
                            action_params[param_name] = context.get(source[8:])
                        elif source.startswith("payload."):
                            action_params[param_name] = payload.get(source[8:])
                        elif source in context:
                            action_params[param_name] = context.get(source)
                        elif source in payload:
                            action_params[param_name] = payload.get(source)
                else:
                    # Default: only pass parameters that the action function expects
                    import inspect
                    sig = inspect.signature(action_func)
                    # Skip instance_id and context (they're passed explicitly)
                    for param_name, param in sig.parameters.items():
                        if param_name not in ['instance_id', 'context']:
                            # Look for parameter in payload first, then context
                            if param_name in payload:
                                action_params[param_name] = payload[param_name]
                            elif param_name in context:
                                action_params[param_name] = context[param_name]
                
                # Execute in thread pool for blocking actions
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    partial(
                        action_func,
                        instance_id=instance_id,
                        context=context,
                        **action_params
                    )
                )
                
                # Success - update TaskExecution
                with Session(engine) as session:
                    task = session.get(TaskExecution, task_execution_id)
                    if task:
                        task.status = "completed"
                        task.completed_at = datetime.now(timezone.utc)
                        task.result = json.dumps(result) if result else None
                        task.retry_count = attempt - 1
                        session.add(task)
                        session.commit()
                    
                    # Update instance context with result
                    if result:
                        instance = session.get(StateMachineInstance, instance_id)
                        if instance:
                            instance.update_context(result)
                            session.add(instance)
                            session.commit()
                
                logger.info(f"Async action completed: {action_name} (job_id={job_id})")
                
                # Clean up pending task reference
                self.pending_tasks.pop(job_id, None)
                return
                
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Async action failed (attempt {attempt}/{max_attempts}): "
                    f"{action_name} - {e}"
                )
                
                # Update retry count
                with Session(engine) as session:
                    task = session.get(TaskExecution, task_execution_id)
                    if task:
                        task.retry_count = attempt
                        session.add(task)
                        session.commit()
                
                if attempt < max_attempts:
                    # Calculate backoff delay
                    if backoff == "exponential":
                        delay = 2 ** attempt
                    else:
                        delay = 5  # Fixed delay
                    
                    await asyncio.sleep(delay)
        
        # All retries exhausted - mark as failed
        with Session(engine) as session:
            task = session.get(TaskExecution, task_execution_id)
            if task:
                task.status = "failed"
                task.completed_at = datetime.now(timezone.utc)
                task.error_message = last_error
                session.add(task)
                session.commit()
        
        logger.error(f"Async action failed permanently: {action_name} (job_id={job_id})")
        self.pending_tasks.pop(job_id, None)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job by job_id."""
        if job_id in self.pending_tasks:
            task = self.pending_tasks[job_id]
            if task.done():
                return {"status": "completed" if not task.exception() else "failed"}
            return {"status": "running"}
        return None
    
    def shutdown(self) -> None:
        """Shutdown the task queue."""
        self._running = False
        self.executor.shutdown(wait=True)
        for task in self.pending_tasks.values():
            task.cancel()
        self.pending_tasks.clear()


def get_task_execution_status(
    session: Session,
    task_execution_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get the status of a task execution from the database.
    
    Args:
        session: Database session
        task_execution_id: ID of the TaskExecution record
        
    Returns:
        Dict with task status details, or None if not found
    """
    task = session.get(TaskExecution, task_execution_id)
    if not task:
        return None
    
    return {
        "id": task.id,
        "status": task.status,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "result": json.loads(task.result) if task.result else None,
        "error_message": task.error_message,
        "retry_count": task.retry_count
    }


def get_transition_task_executions(
    session: Session,
    transition_log_id: int
) -> List[Dict[str, Any]]:
    """
    Get all task executions for a transition.
    
    Args:
        session: Database session
        transition_log_id: ID of the transition log
        
    Returns:
        List of task execution status dicts
    """
    statement = select(TaskExecution, ActionDefinition).join(
        ActionDefinition,
        TaskExecution.action_definition_id == ActionDefinition.id
    ).where(
        TaskExecution.transition_log_id == transition_log_id
    ).order_by(TaskExecution.created_at)
    
    results = session.exec(statement).all()
    
    return [
        {
            "id": task.id,
            "action_name": action_def.name,
            "action_display_name": action_def.display_name,
            "status": task.status,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": json.loads(task.result) if task.result else None,
            "error_message": task.error_message,
            "retry_count": task.retry_count
        }
        for task, action_def in results
    ]
