from typing import Callable, Dict, Optional, List
from dataclasses import dataclass, asdict
import logging
import inspect
import json

logger = logging.getLogger(__name__)


@dataclass
class ActionMetadata:
    """Metadata about an action function for the action library."""
    name: str
    display_name: str
    category: str
    description: str
    python_function: str
    parameters_schema: dict
    is_async: bool
    timeout_seconds: int
    retry_policy: dict
    function: Optional[Callable] = None
    
    def to_dict(self) -> dict:
        """Convert to dict, excluding the function object."""
        data = asdict(self)
        data.pop('function', None)
        return data


ACTION_REGISTRY: Dict[str, ActionMetadata] = {}


def action(
    name: str,
    display_name: str = None,
    category: str = "general",
    description: str = "",
    timeout_seconds: int = 300,
    retry_policy: dict = None
):
    """
    Decorator to register reusable actions in the action library.
    
    Actions registered here become available in the action marketplace
    and can be attached to state machine transitions.
    
    Usage:
        @action(
            name="send_email",
            display_name="Send Email",
            category="communication",
            description="Send email via SMTP"
        )
        def send_email(instance_id: int, context: dict, to: str, subject: str, body: str) -> dict:
            # Implementation
            return {"message_id": "123"}
    
    Args:
        name: Unique identifier for the action
        display_name: Human-readable name (defaults to formatted name)
        category: Category for organization (communication, payment, validation, workflow_control)
        description: What this action does
        timeout_seconds: Maximum execution time
        retry_policy: Dict with max_attempts and backoff strategy
    """
    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        params_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            if param_name in ['instance_id', 'context']:
                continue
            
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation is int:
                    param_type = "integer"
                elif param.annotation is float:
                    param_type = "number"
                elif param.annotation is bool:
                    param_type = "boolean"
                elif param.annotation is dict:
                    param_type = "object"
                elif param.annotation is list:
                    param_type = "array"
            
            params_schema["properties"][param_name] = {"type": param_type}
            
            if param.default == inspect.Parameter.empty:
                params_schema["required"].append(param_name)
        
        metadata = ActionMetadata(
            name=name,
            display_name=display_name or name.replace("_", " ").title(),
            category=category,
            description=description or func.__doc__ or "",
            python_function=f"{func.__module__}.{func.__name__}",
            parameters_schema=params_schema,
            is_async=inspect.iscoroutinefunction(func),
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy or {"max_attempts": 3, "backoff": "exponential"},
            function=func
        )
        
        ACTION_REGISTRY[name] = metadata
        logger.info(f"Registered action: {name} ({category}) -> {func.__name__}")
        return func
    
    return decorator


def get_action(name: str) -> Optional[ActionMetadata]:
    """Retrieve action metadata by name."""
    return ACTION_REGISTRY.get(name)


def get_action_function(name: str) -> Optional[Callable]:
    """Retrieve just the function for an action."""
    metadata = ACTION_REGISTRY.get(name)
    return metadata.function if metadata else None


def list_actions(category: Optional[str] = None) -> List[ActionMetadata]:
    """List all actions, optionally filtered by category."""
    actions = list(ACTION_REGISTRY.values())
    if category:
        actions = [a for a in actions if a.category == category]
    return actions


def get_categories() -> List[str]:
    """Get all unique action categories."""
    return sorted(set(a.category for a in ACTION_REGISTRY.values()))


def get_action_names() -> List[str]:
    """Get list of all registered action names."""
    return list(ACTION_REGISTRY.keys())


def sync_actions_to_db(session):
    """
    Synchronize in-memory action registry to database.
    This should be called on application startup.
    """
    from app.models import ActionDefinition
    
    for action_name, metadata in ACTION_REGISTRY.items():
        existing = session.query(ActionDefinition).filter(
            ActionDefinition.name == action_name
        ).first()
        
        if existing:
            existing.display_name = metadata.display_name
            existing.category = metadata.category
            existing.description = metadata.description
            existing.python_function = metadata.python_function
            existing.parameters_schema = json.dumps(metadata.parameters_schema)
            existing.is_async = metadata.is_async
            existing.timeout_seconds = metadata.timeout_seconds
            existing.retry_policy = json.dumps(metadata.retry_policy)
            logger.info(f"Updated action in DB: {action_name}")
        else:
            action_def = ActionDefinition(
                name=action_name,
                display_name=metadata.display_name,
                category=metadata.category,
                description=metadata.description,
                python_function=metadata.python_function,
                parameters_schema=json.dumps(metadata.parameters_schema),
                is_async=metadata.is_async,
                timeout_seconds=metadata.timeout_seconds,
                retry_policy=json.dumps(metadata.retry_policy)
            )
            session.add(action_def)
            logger.info(f"Added action to DB: {action_name}")
    
    session.commit()
    logger.info(f"Synced {len(ACTION_REGISTRY)} actions to database")
