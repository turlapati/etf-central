"""
Payment actions: debit, credit, refund operations.
"""
import logging
from typing import Dict, Any
from app.registry import action
from app.utils.mocks import payment_gateway

logger = logging.getLogger(__name__)


@action(
    name="debit_account",
    display_name="Debit Account",
    category="payment",
    description="Debit amount from an account",
    timeout_seconds=120,
    retry_policy={"max_attempts": 3, "backoff": "exponential"}
)
def debit_account(instance_id: int, context: Dict[str, Any], account_id: str, amount: float) -> Dict[str, Any]:
    """
    Debit an amount from an account.
    
    Args:
        instance_id: State machine instance ID
        context: Current instance context
        account_id: Account to debit from
        amount: Amount to debit
    
    Returns:
        Dict with transaction details
    """
    logger.info(f"[Instance {instance_id}] Debiting {amount} from account {account_id}")
    
    try:
        result = payment_gateway.debit_account(account_id, amount)
        logger.info(f"[Instance {instance_id}] Debit successful: {result['transaction_id']}")
        return {
            "debit_successful": True,
            "transaction_id": result["transaction_id"],
            "amount": amount,
            "account_id": account_id,
            "timestamp": result["timestamp"]
        }
    except Exception as e:
        logger.error(f"[Instance {instance_id}] Debit failed: {str(e)}")
        raise


@action(
    name="credit_account",
    display_name="Credit Account",
    category="payment",
    description="Credit amount to an account",
    timeout_seconds=120,
    retry_policy={"max_attempts": 3, "backoff": "exponential"}
)
def credit_account(instance_id: int, context: Dict[str, Any], account_id: str, amount: float) -> Dict[str, Any]:
    """
    Credit an amount to an account.
    
    Args:
        instance_id: State machine instance ID
        context: Current instance context
        account_id: Account to credit to
        amount: Amount to credit
    
    Returns:
        Dict with transaction details
    """
    logger.info(f"[Instance {instance_id}] Crediting {amount} to account {account_id}")
    
    try:
        result = payment_gateway.credit_account(account_id, amount)
        logger.info(f"[Instance {instance_id}] Credit successful: {result['transaction_id']}")
        return {
            "credit_successful": True,
            "transaction_id": result["transaction_id"],
            "amount": amount,
            "account_id": account_id,
            "timestamp": result["timestamp"]
        }
    except Exception as e:
        logger.error(f"[Instance {instance_id}] Credit failed: {str(e)}")
        raise


@action(
    name="refund_account",
    display_name="Refund Account",
    category="payment",
    description="Refund amount to an account (compensating transaction)",
    timeout_seconds=120,
    retry_policy={"max_attempts": 5, "backoff": "exponential"}
)
def refund_account(instance_id: int, context: Dict[str, Any], account_id: str, amount: float) -> Dict[str, Any]:
    """
    Refund an amount to an account (compensating transaction).
    
    This is a critical operation for rollbacks and should have higher retry attempts.
    """
    logger.info(f"[Instance {instance_id}] Refunding {amount} to account {account_id}")
    
    try:
        result = payment_gateway.credit_account(account_id, amount)
        logger.info(f"[Instance {instance_id}] Refund successful: {result['transaction_id']}")
        return {
            "refund_successful": True,
            "refund_transaction_id": result["transaction_id"],
            "refund_amount": amount,
            "refund_account_id": account_id,
            "timestamp": result["timestamp"]
        }
    except Exception as e:
        logger.critical(f"[Instance {instance_id}] REFUND FAILED: {str(e)}")
        raise
