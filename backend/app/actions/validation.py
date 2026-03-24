"""
Validation actions: data validation, verification checks.
"""
import logging
from typing import Dict, Any
from app.registry import action
from app.utils.mocks import kyc_verification, credit_bureau

logger = logging.getLogger(__name__)


@action(
    name="validate_transfer_request",
    display_name="Validate Transfer Request",
    category="validation",
    description="Validate transfer request parameters",
    timeout_seconds=30
)
def validate_transfer_request(
    instance_id: int, 
    context: Dict[str, Any], 
    sender_id: str, 
    receiver_id: str, 
    amount: float
) -> Dict[str, Any]:
    """
    Validate a transfer request.
    
    Checks:
    - Required fields present
    - Amount is positive
    - Sender and receiver are different
    """
    logger.info(f"[Instance {instance_id}] Validating transfer request")
    
    errors = []
    
    if not sender_id:
        errors.append("sender_id is required")
    if not receiver_id:
        errors.append("receiver_id is required")
    if sender_id == receiver_id:
        errors.append("sender and receiver must be different")
    if amount <= 0:
        errors.append("amount must be positive")
    
    if errors:
        raise ValueError(f"Validation failed: {', '.join(errors)}")
    
    logger.info(f"[Instance {instance_id}] Transfer validation passed")
    return {
        "validation_passed": True,
        "validated_amount": amount,
        "validated_sender": sender_id,
        "validated_receiver": receiver_id
    }


@action(
    name="verify_kyc_documents",
    display_name="Verify KYC Documents",
    category="validation",
    description="Verify KYC documents automatically",
    timeout_seconds=180
)
def verify_kyc_documents(instance_id: int, context: Dict[str, Any], documents: dict) -> Dict[str, Any]:
    """
    Verify KYC documents using automated verification service.
    
    Returns verification status and next action recommendation.
    """
    logger.info(f"[Instance {instance_id}] Verifying KYC documents")
    
    if not documents:
        raise ValueError("No documents provided for verification")
    
    result = kyc_verification.verify_documents(documents)
    
    logger.info(f"[Instance {instance_id}] KYC verification: {result['status']}")
    
    return {
        "verification_id": result["verification_id"],
        "verification_status": result["status"],
        "verification_passed": result["status"] == "passed",
        "verified_at": result["verified_at"],
        "documents_verified": list(documents.keys())
    }


@action(
    name="check_credit_score",
    display_name="Check Credit Score",
    category="validation",
    description="Retrieve credit score from credit bureau",
    timeout_seconds=120
)
def check_credit_score(instance_id: int, context: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Check credit score for a user.
    
    Returns score and risk category.
    """
    logger.info(f"[Instance {instance_id}] Checking credit score for user {user_id}")
    
    result = credit_bureau.get_credit_score(user_id)
    score = result["credit_score"]
    
    if score >= 700:
        risk_category = "low"
        recommendation = "auto_approve"
    elif score >= 650:
        risk_category = "medium"
        recommendation = "manual_review"
    else:
        risk_category = "high"
        recommendation = "auto_reject"
    
    logger.info(f"[Instance {instance_id}] Credit score: {score} ({risk_category})")
    
    return {
        "credit_score": score,
        "risk_category": risk_category,
        "recommendation": recommendation,
        "checked_at": result["checked_at"]
    }
