import random
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MockPaymentGateway:
    """Mock payment service with configurable failure rates."""
    
    def __init__(self, debit_failure_rate: float = 0.1, credit_failure_rate: float = 0.05):
        self.debit_failure_rate = debit_failure_rate
        self.credit_failure_rate = credit_failure_rate
    
    def debit_account(self, account_id: str, amount: float) -> Dict[str, Any]:
        """
        Simulate debiting an account.
        Returns transaction details or raises exception on failure.
        """
        logger.info(f"MockPaymentGateway: Debiting {amount} from account {account_id}")
        
        if random.random() < self.debit_failure_rate:
            logger.error(f"MockPaymentGateway: Debit failed for account {account_id}")
            raise Exception(f"Payment gateway error: Failed to debit account {account_id}")
        
        transaction_id = f"TXN-DEBIT-{random.randint(10000, 99999)}"
        logger.info(f"MockPaymentGateway: Debit successful - {transaction_id}")
        
        return {
            "transaction_id": transaction_id,
            "account_id": account_id,
            "amount": amount,
            "type": "debit",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def credit_account(self, account_id: str, amount: float) -> Dict[str, Any]:
        """
        Simulate crediting an account.
        Returns transaction details or raises exception on failure.
        """
        logger.info(f"MockPaymentGateway: Crediting {amount} to account {account_id}")
        
        if random.random() < self.credit_failure_rate:
            logger.error(f"MockPaymentGateway: Credit failed for account {account_id}")
            raise Exception(f"Payment gateway error: Failed to credit account {account_id}")
        
        transaction_id = f"TXN-CREDIT-{random.randint(10000, 99999)}"
        logger.info(f"MockPaymentGateway: Credit successful - {transaction_id}")
        
        return {
            "transaction_id": transaction_id,
            "account_id": account_id,
            "amount": amount,
            "type": "credit",
            "timestamp": datetime.utcnow().isoformat()
        }


class MockEmailService:
    """Mock email service with configurable failure rate."""
    
    def __init__(self, failure_rate: float = 0.02):
        self.failure_rate = failure_rate
    
    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Simulate sending an email.
        Returns email details or raises exception on failure.
        """
        logger.info(f"MockEmailService: Sending email to {to} - Subject: {subject}")
        
        if random.random() < self.failure_rate:
            logger.error(f"MockEmailService: Failed to send email to {to}")
            raise Exception(f"Email service error: Failed to send email to {to}")
        
        message_id = f"MSG-{random.randint(100000, 999999)}"
        logger.info(f"MockEmailService: Email sent successfully - {message_id}")
        
        return {
            "message_id": message_id,
            "to": to,
            "subject": subject,
            "sent_at": datetime.utcnow().isoformat()
        }


class MockCreditBureau:
    """Mock credit bureau service."""
    
    def get_credit_score(self, user_id: str) -> Dict[str, Any]:
        """
        Simulate fetching a credit score.
        Returns random score between 300-850.
        """
        score = random.randint(300, 850)
        logger.info(f"MockCreditBureau: Credit score for {user_id}: {score}")
        
        return {
            "user_id": user_id,
            "credit_score": score,
            "bureau": "MockBureau",
            "retrieved_at": datetime.utcnow().isoformat()
        }


class MockKYCVerification:
    """Mock KYC verification service."""
    
    def __init__(self, auto_pass_rate: float = 0.7):
        self.auto_pass_rate = auto_pass_rate
    
    def verify_documents(self, documents: Dict[str, str]) -> Dict[str, Any]:
        """
        Simulate document verification.
        70% pass rate for auto-verification.
        """
        logger.info(f"MockKYCVerification: Verifying documents: {list(documents.keys())}")
        
        passed = random.random() < self.auto_pass_rate
        verification_id = f"KYC-{random.randint(100000, 999999)}"
        
        result = {
            "verification_id": verification_id,
            "status": "passed" if passed else "needs_review",
            "documents_checked": list(documents.keys()),
            "verified_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"MockKYCVerification: Result - {result['status']}")
        return result


# Singleton instances
payment_gateway = MockPaymentGateway()
email_service = MockEmailService()
credit_bureau = MockCreditBureau()
kyc_verification = MockKYCVerification()
