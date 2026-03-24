"""
Communication actions: email, SMS, notifications.
"""
import logging
from typing import Dict, Any
from app.registry import action
from app.utils.mocks import email_service

logger = logging.getLogger(__name__)


@action(
    name="send_email",
    display_name="Send Email",
    category="communication",
    description="Send email to a recipient",
    timeout_seconds=60
)
def send_email(instance_id: int, context: Dict[str, Any], to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send an email message.
    
    Args:
        instance_id: State machine instance ID
        context: Current instance context
        to: Recipient email address
        subject: Email subject
        body: Email body content
    
    Returns:
        Dict with message_id and status
    """
    logger.info(f"[Instance {instance_id}] Sending email to {to}")
    
    try:
        result = email_service.send_email(to=to, subject=subject, body=body)
        logger.info(f"[Instance {instance_id}] Email sent: {result['message_id']}")
        return {
            "email_sent": True,
            "message_id": result["message_id"],
            "sent_to": to
        }
    except Exception as e:
        logger.error(f"[Instance {instance_id}] Email failed: {str(e)}")
        return {
            "email_sent": False,
            "error": str(e)
        }


@action(
    name="send_welcome_email",
    display_name="Send Welcome Email",
    category="communication",
    description="Send welcome email to user",
    timeout_seconds=60
)
def send_welcome_email(instance_id: int, context: Dict[str, Any], user_email: str) -> Dict[str, Any]:
    """Send a welcome email to a new user."""
    logger.info(f"[Instance {instance_id}] Sending welcome email to {user_email}")
    
    try:
        result = email_service.send_email(
            to=user_email,
            subject="Welcome!",
            body="Welcome to our platform. Your account has been verified."
        )
        return {
            "welcome_email_sent": True,
            "message_id": result["message_id"]
        }
    except Exception as e:
        logger.error(f"[Instance {instance_id}] Welcome email failed: {str(e)}")
        return {
            "welcome_email_sent": False,
            "error": str(e)
        }


@action(
    name="send_rejection_email",
    display_name="Send Rejection Email",
    category="communication",
    description="Send rejection notification email",
    timeout_seconds=60
)
def send_rejection_email(
    instance_id: int, 
    context: Dict[str, Any], 
    user_email: str, 
    reason: str = "Requirements not met"
) -> Dict[str, Any]:
    """Send a rejection email with reason."""
    logger.info(f"[Instance {instance_id}] Sending rejection email to {user_email}")
    
    try:
        result = email_service.send_email(
            to=user_email,
            subject="Application Status",
            body=f"Unfortunately, your application has been rejected. Reason: {reason}"
        )
        return {
            "rejection_email_sent": True,
            "message_id": result["message_id"],
            "reason": reason
        }
    except Exception as e:
        logger.error(f"[Instance {instance_id}] Rejection email failed: {str(e)}")
        return {
            "rejection_email_sent": False,
            "error": str(e)
        }
