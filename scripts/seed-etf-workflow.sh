#!/bin/bash
# Seeds the ETF Creation/Redemption order workflow into the backend.
#
# Workflow models the real-world C/R lifecycle:
#   NEW → SUBMITTED → VALIDATED → AFFIRMED → PRICED → SETTLING → SETTLED
# With amendment loop, operational review, and cancellation branches.
set -e

BASE_URL="${TRIDENT_URL:-http://localhost:8000}"

echo "============================================"
echo "  ETF Central — Seed Workflow"
echo "============================================"
echo ""

# The Mermaid definition uses note blocks for payload schemas.
# This drives both backend validation and (future) frontend form generation.
MERMAID='stateDiagram-v2
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
        description: "Issuer affirms the order — binding contract established"
        payload:
            affirmed_by: string, optional
            estimated_cash_amount: number, optional
            pricing_method: string, optional [NAV_NEXT, FIXED_NAV]
    end note

    note right of PRICED
        trigger_type: api
        description: "NAV struck at EOD — final settlement value determined"
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
        description: "DVP completed — shares issued/cancelled, cash settled"
        payload:
            settlement_ref: string, optional
            depository: string, optional [DTC, NSCC_CNS, EUROCLEAR, CREST]
            settled_date: string, optional
    end note

    note right of AMENDABLE
        trigger_type: api
        description: "Soft rejection — order can be amended and resubmitted"
        payload:
            amendment_reason: string, optional
            amended_fields: string, optional
    end note

    note right of OPS_REVIEW
        trigger_type: api
        description: "Settlement failed — manual intervention required"
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
    end note'

PAYLOAD=$(cat <<EOF
{
  "name": "etf_order",
  "mermaid_definition": $(echo "$MERMAID" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))"),
  "initial_state": "NEW",
  "description": "ETF Creation/Redemption order lifecycle — models the full C/R flow from AP submission through gateway validation, issuer affirmation, NAV pricing, and DTC settlement."
}
EOF
)

echo "==> Creating ETF order workflow..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/state-machines/definitions" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
  echo "    Workflow created successfully."
  echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
elif echo "$BODY" | grep -qi "already exists\|duplicate\|unique"; then
  echo "    Workflow already exists — OK."
else
  echo "    Response ($HTTP_CODE): $BODY"
fi

echo ""
echo "==> Reloading trigger routes..."
curl -s -X POST "$BASE_URL/admin/reload-routes" | python3 -m json.tool 2>/dev/null

echo ""
echo "============================================"
echo "  Workflow seeded. Dynamic trigger routes:"
echo ""
echo "  POST /api/etf_order/{id}/SUBMIT"
echo "  POST /api/etf_order/{id}/PASS_VALIDATION"
echo "  POST /api/etf_order/{id}/REJECT_SOFT"
echo "  POST /api/etf_order/{id}/REJECT_HARD"
echo "  POST /api/etf_order/{id}/AFFIRM"
echo "  POST /api/etf_order/{id}/REJECT"
echo "  POST /api/etf_order/{id}/PRICE"
echo "  POST /api/etf_order/{id}/GENERATE_SETTLEMENT"
echo "  POST /api/etf_order/{id}/CONFIRM_SETTLEMENT"
echo "  POST /api/etf_order/{id}/SETTLEMENT_FAIL"
echo "  POST /api/etf_order/{id}/RETRY_SETTLEMENT"
echo "  POST /api/etf_order/{id}/ESCALATE_CANCEL"
echo "  POST /api/etf_order/{id}/AMEND_RESUBMIT"
echo "  POST /api/etf_order/{id}/ABANDON"
echo "  POST /api/etf_order/{id}/CANCEL"
echo ""
echo "  API docs: $BASE_URL/docs"
echo "============================================"
