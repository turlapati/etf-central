"""
Auto-seed the ETF order workflow definition on startup.

Embeds the Mermaid definition directly so the app is self-contained
and doesn't depend on an external seed script for basic functionality.
"""
import logging
from sqlmodel import Session

from app.models import StateMachineDefinition
from app.engine import MermaidParser
from app.services.transition_metadata_service import populate_transition_metadata

logger = logging.getLogger(__name__)

ETF_ORDER_MERMAID = """\
stateDiagram-v2
    direction LR

    [*] --> NEW : CREATE

    state NEW
    state SUBMITTED
    state VALIDATED
    state AFFIRMED
    state PRICED
    state SETTLING
    state SETTLED
    state AMENDABLE
    state OPS_REVIEW
    state REJECTED
    state CANCELLED

    %% Submission Flow
    NEW --> SUBMITTED : SUBMIT

    %% Gateway Validation
    SUBMITTED --> VALIDATED : PASS_VALIDATION
    SUBMITTED --> AMENDABLE : REJECT_SOFT
    SUBMITTED --> REJECTED : REJECT_HARD

    %% Issuer Decision
    VALIDATED --> AFFIRMED : AFFIRM
    VALIDATED --> REJECTED : REJECT
    VALIDATED --> CANCELLED : CANCEL

    %% Post-Trade Pricing (EOD NAV strike)
    AFFIRMED --> PRICED : PRICE
    AFFIRMED --> CANCELLED : CANCEL

    %% Settlement
    PRICED --> SETTLING : GENERATE_SETTLEMENT
    SETTLING --> SETTLED : CONFIRM_SETTLEMENT
    SETTLING --> OPS_REVIEW : SETTLEMENT_FAIL

    %% Ops Review (manual intervention)
    OPS_REVIEW --> SETTLING : RETRY_SETTLEMENT
    OPS_REVIEW --> CANCELLED : ESCALATE_CANCEL

    %% Amendment Loop
    AMENDABLE --> SUBMITTED : AMEND_RESUBMIT
    AMENDABLE --> CANCELLED : ABANDON

    %% Terminal states
    SETTLED --> [*]
    REJECTED --> [*]
    CANCELLED --> [*]

    %% ---------------------------------------------------------
    %% PAYLOAD DEFINITIONS (note blocks drive form generation)
    %% ---------------------------------------------------------

    note right of NEW
        trigger_type: api
        payload:
            action: string, required [CREATE, REDEEM]
            ticker: string, required [SPY, QQQ, IWM, VOO, TLT, XLF, HYG, EEM, GLD, VTI]
            units: integer, required
            unit_size: integer, required
            method: string, required [Cash, In-Kind]
            basket_type: string, required [Standard, Custom]
            settlement_period: string, optional [T0, T1, T2]
            ap_account_id: string, optional
    end note

    note right of VALIDATED
        trigger_type: api
        description: "Gateway validation checks passed"
        payload:
            validation_id: string, optional
            checks_passed: list [KYC, CREDIT_LIMIT, UNIT_SIZE, CUTOFF, AP_AUTH]
    end note

    note right of AFFIRMED
        trigger_type: api
        description: "Issuer affirms the order -- binding contract established"
        payload:
            affirmed_by: string, optional
            estimated_cash_amount: number, optional
            pricing_method: string, optional [NAV_NEXT, FIXED_NAV]
    end note

    note right of PRICED
        trigger_type: api
        description: "NAV struck at EOD -- final settlement value determined"
        payload:
            nav_date: string, optional
            nav_per_unit: number, optional
            gross_trade_value: number, optional
            cash_component: number, optional
            net_settlement_amount: number, optional
    end note

    note right of SETTLING
        trigger_type: api
        description: "Settlement instructions generated and sent to DTC/custodian"
        payload:
            dtc_instruction_id: string, optional
            settlement_date: string, optional
    end note

    note right of SETTLED
        trigger_type: api
        description: "DVP completed -- shares issued/cancelled, cash settled"
        payload:
            settlement_ref: string, optional
            depository: string, optional [DTC, NSCC_CNS, EUROCLEAR, CREST]
            settled_date: string, optional
    end note

    note right of AMENDABLE
        trigger_type: api
        description: "Soft rejection -- order can be amended and resubmitted"
        payload:
            amendment_reason: string, optional
            amended_fields: string, optional
    end note

    note right of OPS_REVIEW
        trigger_type: api
        description: "Settlement failed -- manual intervention required"
        payload:
            fail_reason: string, optional
            fail_type: string, optional [COUNTERPARTY_FAIL, BASKET_INCOMPLETE, DTC_REJECT, CASH_SHORTFALL]
    end note

    note right of REJECTED
        trigger_type: api
        payload:
            reject_reason: string, optional
            reject_code: string, optional [INVALID_AP, CUTOFF_MISSED, CREDIT_BREACH, INVENTORY_SHORTAGE]
    end note

    note right of CANCELLED
        trigger_type: api
        payload:
            cancel_reason: string, optional
            cancelled_by: string, optional
    end note"""


def seed_etf_workflow(session: Session) -> StateMachineDefinition:
    """Create the etf_order workflow definition in the database."""
    parser = MermaidParser(ETF_ORDER_MERMAID)

    definition = StateMachineDefinition(
        name="etf_order",
        mermaid_definition=ETF_ORDER_MERMAID,
        initial_state=parser.initial_state or "NEW",
        description=(
            "ETF Creation/Redemption order lifecycle — models the full C/R flow "
            "from AP submission through gateway validation, issuer affirmation, "
            "NAV pricing, and DTC settlement."
        ),
        version=1,
        is_active=True,
        created_by="auto-seed",
    )

    session.add(definition)
    session.commit()
    session.refresh(definition)

    try:
        populate_transition_metadata(session, definition)
    except Exception as e:
        logger.warning(f"Failed to populate transition metadata: {e}")

    return definition
