"""
Workflow control actions: logging, state management, conditional routing.
"""
import logging
from typing import Dict, Any
from datetime import datetime
from app.registry import action

logger = logging.getLogger(__name__)


@action(
    name="log_transition",
    display_name="Log Transition",
    category="workflow_control",
    description="Log state transition for audit trail",
    timeout_seconds=10
)
def log_transition(
    instance_id: int, 
    context: Dict[str, Any], 
    event_type: str, 
    details: str = ""
) -> Dict[str, Any]:
    """
    Log a transition event for audit purposes.
    """
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"[Instance {instance_id}] Audit log: {event_type} - {details}")
    
    return {
        "logged_at": timestamp,
        "event_type": event_type,
        "log_details": details
    }


@action(
    name="set_status_completed",
    display_name="Set Status to Completed",
    category="workflow_control",
    description="Mark instance as completed",
    timeout_seconds=10
)
def set_status_completed(instance_id: int, context: Dict[str, Any]) -> Dict[str, Any]:
    """Mark the state machine instance as completed."""
    logger.info(f"[Instance {instance_id}] Setting status to completed")
    return {
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat()
    }


@action(
    name="set_status_failed",
    display_name="Set Status to Failed",
    category="workflow_control",
    description="Mark instance as failed",
    timeout_seconds=10
)
def set_status_failed(instance_id: int, context: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    """Mark the state machine instance as failed."""
    logger.info(f"[Instance {instance_id}] Setting status to failed: {reason}")
    return {
        "status": "failed",
        "failed_at": datetime.utcnow().isoformat(),
        "failure_reason": reason
    }


@action(
    name="route_by_credit_score",
    display_name="Route by Credit Score",
    category="workflow_control",
    description="Determine next trigger based on credit score",
    timeout_seconds=10
)
def route_by_credit_score(instance_id: int, context: Dict[str, Any], credit_score: int) -> Dict[str, Any]:
    """
    Conditional routing based on credit score.
    
    Returns the next trigger name to fire.
    """
    logger.info(f"[Instance {instance_id}] Routing based on credit score: {credit_score}")
    
    if credit_score >= 700:
        next_trigger = "high_score"
    elif credit_score >= 650:
        next_trigger = "medium_score"
    else:
        next_trigger = "low_score"
    
    logger.info(f"[Instance {instance_id}] Routing to: {next_trigger}")
    
    return {
        "routing_decision": next_trigger,
        "next_trigger": next_trigger,
        "credit_score_used": credit_score
    }


@action(
    name="route_by_verification_status",
    display_name="Route by Verification Status",
    category="workflow_control",
    description="Determine next trigger based on verification result",
    timeout_seconds=10
)
def route_by_verification_status(
    instance_id: int, 
    context: Dict[str, Any], 
    verification_status: str
) -> Dict[str, Any]:
    """
    Conditional routing based on KYC verification status.
    
    Returns the next trigger name to fire.
    """
    logger.info(f"[Instance {instance_id}] Routing based on verification: {verification_status}")
    
    if verification_status == "passed":
        next_trigger = "auto_approve"
    else:
        next_trigger = "needs_review"
    
    logger.info(f"[Instance {instance_id}] Routing to: {next_trigger}")
    
    return {
        "routing_decision": next_trigger,
        "next_trigger": next_trigger,
        "verification_status_used": verification_status
    }
