#!/usr/bin/env bash
set -o igncr 2>/dev/null || true
# =============================================================================
# ETF Order Workflow – End-to-end curl test script
#
# Walks every reachable path in the etf_order state machine and verifies each
# transition against the live backend API.  Also pre-populates the blotter with
# realistic order records in various terminal and in-progress states.
#
# State machine:
#   NEW → SUBMITTED → VALIDATED → AFFIRMED → PRICED → SETTLING → SETTLED
#   With: amendment loop (AMENDABLE), ops review (OPS_REVIEW), rejection
#         (REJECTED), and cancellation (CANCELLED) branches.
#
# Usage:
#   chmod +x scripts/etf-workflow-test.sh
#   ./scripts/etf-workflow-test.sh
#
# Requirements: curl, python3 (for JSON field extraction).
# Exit code: 0 = all assertions passed, 1 = one or more failures.
# =============================================================================

export MSYS_NO_PATHCONV=1

BASE="${ETF_CENTRAL_URL:-http://localhost:8000}"
PASS=0
FAIL=0

# Resolve Python interpreter
if python3 -c "" 2>/dev/null; then
  PY=python3
elif python -c "" 2>/dev/null; then
  PY=python
else
  echo "ERROR: no working Python 3 interpreter found." >&2
  exit 1
fi

# ── startup diagnostics ─────────────────────────────────────────────────────

echo "── env ──────────────────────────────────────────────────────────────────────"
echo "  bash       : ${BASH_VERSION}"
echo "  python     : ${PY} ($(${PY} --version 2>&1))"
echo "  curl       : $(curl --version | head -1)"
echo "  base url   : ${BASE}"

echo "── server reachability ──────────────────────────────────────────────────────"
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "${BASE}/health")
echo "  GET ${BASE}/health  →  HTTP ${HEALTH}"
if [ "$HEALTH" != "200" ]; then
  echo "  ERROR: cannot reach ${BASE} – is the server running?" >&2
  exit 1
fi
echo "─────────────────────────────────────────────────────────────────────────────"
echo ""

# ── helpers ──────────────────────────────────────────────────────────────────

green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }

# trigger ID TRIGGER PAYLOAD_JSON EXPECTED_NEW_STATE
trigger() {
  local id="$1" trigger_name="$2" payload="$3" expected="$4"
  local url="${BASE}/api/etf_order/${id}/${trigger_name}"
  local resp
  resp=$(curl -s -X POST "$url" -H "Content-Type: application/json" -d "$payload")
  local actual_state
  actual_state=$(echo "$resp" | $PY -c "import json,sys;d=json.load(sys.stdin);print(d.get('new_state','?'))" 2>/dev/null)
  local ok
  ok=$(echo "$resp" | $PY -c "import json,sys;d=json.load(sys.stdin);print(d.get('success',False))" 2>/dev/null)

  if [ "$ok" = "True" ] && [ "$actual_state" = "$expected" ]; then
    green "  ✓ ${trigger_name} → ${actual_state}"
    PASS=$((PASS + 1))
  else
    local err
    err=$(echo "$resp" | $PY -c "import json,sys;d=json.load(sys.stdin);print(d.get('error',''))" 2>/dev/null)
    red "  ✗ ${trigger_name}: expected ${expected}, got ${actual_state}. Error: ${err}"
    FAIL=$((FAIL + 1))
  fi
}

# trigger_fail ID TRIGGER PAYLOAD_JSON EXPECTED_ERROR_SUBSTR
trigger_fail() {
  local id="$1" trigger_name="$2" payload="$3" expected_err="$4"
  local url="${BASE}/api/etf_order/${id}/${trigger_name}"
  local resp
  resp=$(curl -s -X POST "$url" -H "Content-Type: application/json" -d "$payload")
  local ok
  ok=$(echo "$resp" | $PY -c "import json,sys;d=json.load(sys.stdin);print(d.get('success',False))" 2>/dev/null)
  local err
  err=$(echo "$resp" | $PY -c "import json,sys;d=json.load(sys.stdin);print(d.get('error',''))" 2>/dev/null)

  if [ "$ok" = "False" ] && echo "$err" | grep -qi "$expected_err"; then
    green "  ✓ ${trigger_name} correctly rejected: ${err}"
    PASS=$((PASS + 1))
  else
    red "  ✗ ${trigger_name}: expected failure containing '${expected_err}', got success=${ok}, error=${err}"
    FAIL=$((FAIL + 1))
  fi
}

# create_instance CONTEXT_JSON → prints the new instance id
create_instance() {
  local context="$1"
  local resp
  resp=$(curl -s -X POST "${BASE}/api/state-machines/instances" \
    -H "Content-Type: application/json" \
    -d "{\"workflow_name\":\"etf_order\",\"context\":${context}}")
  echo "$resp" | $PY -c "import json,sys;print(json.load(sys.stdin)['id'])" 2>/dev/null
}

# ── shared payloads ──────────────────────────────────────────────────────────

# SUBMIT requires: action, ticker, units, unit_size, method, basket_type
ORDER_CREATE_SPY='{
  "action": "CREATE",
  "ticker": "SPY",
  "units": 500,
  "unit_size": 50000,
  "method": "Cash",
  "basket_type": "Standard"
}'

ORDER_CREATE_QQQ='{
  "action": "CREATE",
  "ticker": "QQQ",
  "units": 200,
  "unit_size": 50000,
  "method": "In-Kind",
  "basket_type": "Standard"
}'

ORDER_REDEEM_IWM='{
  "action": "REDEEM",
  "ticker": "IWM",
  "units": 300,
  "unit_size": 25000,
  "method": "Cash",
  "basket_type": "Custom"
}'

ORDER_CREATE_VOO='{
  "action": "CREATE",
  "ticker": "VOO",
  "units": 1000,
  "unit_size": 50000,
  "method": "In-Kind",
  "basket_type": "Standard"
}'

ORDER_REDEEM_TLT='{
  "action": "REDEEM",
  "ticker": "TLT",
  "units": 750,
  "unit_size": 25000,
  "method": "Cash",
  "basket_type": "Standard"
}'

ORDER_CREATE_XLF='{
  "action": "CREATE",
  "ticker": "XLF",
  "units": 400,
  "unit_size": 50000,
  "method": "Cash",
  "basket_type": "Custom"
}'

ORDER_CREATE_GLD='{
  "action": "CREATE",
  "ticker": "GLD",
  "units": 150,
  "unit_size": 50000,
  "method": "In-Kind",
  "basket_type": "Standard"
}'

ORDER_REDEEM_EEM='{
  "action": "REDEEM",
  "ticker": "EEM",
  "units": 600,
  "unit_size": 25000,
  "method": "Cash",
  "basket_type": "Standard"
}'

ORDER_CREATE_HYG='{
  "action": "CREATE",
  "ticker": "HYG",
  "units": 250,
  "unit_size": 50000,
  "method": "Cash",
  "basket_type": "Standard"
}'

ORDER_CREATE_VTI='{
  "action": "CREATE",
  "ticker": "VTI",
  "units": 800,
  "unit_size": 50000,
  "method": "In-Kind",
  "basket_type": "Custom"
}'

# Downstream trigger payloads (all optional fields)
PASS_VALIDATION='{
  "validation_id": "VAL-001",
  "checks_passed": ["KYC", "CREDIT_LIMIT", "UNIT_SIZE", "CUTOFF", "AP_AUTH"]
}'

AFFIRM='{
  "affirmed_by": "issuer-desk-001",
  "estimated_cash_amount": 25250000.00,
  "pricing_method": "NAV_NEXT"
}'

PRICE='{
  "nav_date": "2026-03-20",
  "nav_per_unit": 505.00,
  "gross_trade_value": 25250000.00,
  "cash_component": 1250.00,
  "net_settlement_amount": 25248750.00
}'

GEN_SETTLEMENT='{
  "dtc_instruction_id": "DTC-2026-0320-001",
  "settlement_date": "2026-03-22"
}'

CONFIRM_SETTLE='{
  "settlement_ref": "STLMT-2026-0322-001",
  "depository": "DTC",
  "settled_date": "2026-03-22"
}'

REJECT_SOFT_PAYLOAD='{
  "amendment_reason": "Unit size below minimum for cash creation",
  "amended_fields": "units"
}'

REJECT_HARD_PAYLOAD='{
  "reject_reason": "AP authorization expired",
  "reject_code": "INVALID_AP"
}'

REJECT_PAYLOAD='{
  "reject_reason": "Order arrived after cutoff",
  "reject_code": "CUTOFF_MISSED"
}'

CANCEL_PAYLOAD='{
  "cancel_reason": "Client requested cancellation",
  "cancelled_by": "ap-desk-002"
}'

SETTLEMENT_FAIL_PAYLOAD='{
  "fail_reason": "Counterparty failed to deliver basket",
  "fail_type": "COUNTERPARTY_FAIL"
}'

AMEND_RESUBMIT_PAYLOAD='{
  "amendment_reason": "Corrected unit count to meet minimum",
  "amended_fields": "units"
}'

# =============================================================================
# Path 1: Happy path – full lifecycle to settlement
# NEW → SUBMITTED → VALIDATED → AFFIRMED → PRICED → SETTLING → SETTLED
# =============================================================================

echo ""
yellow "═══ Path 1: Happy path  NEW → SUBMITTED → VALIDATED → AFFIRMED → PRICED → SETTLING → SETTLED ═══"
ID=$(create_instance "$ORDER_CREATE_SPY")
echo "  Instance id: ${ID}"

trigger "$ID" "SUBMIT"              "$ORDER_CREATE_SPY"  "SUBMITTED"
trigger "$ID" "PASS_VALIDATION"     "$PASS_VALIDATION"   "VALIDATED"
trigger "$ID" "AFFIRM"              "$AFFIRM"            "AFFIRMED"
trigger "$ID" "PRICE"               "$PRICE"             "PRICED"
trigger "$ID" "GENERATE_SETTLEMENT" "$GEN_SETTLEMENT"    "SETTLING"
trigger "$ID" "CONFIRM_SETTLEMENT"  "$CONFIRM_SETTLE"    "SETTLED"

# =============================================================================
# Path 2: Hard rejection at gateway
# NEW → SUBMITTED → REJECTED
# =============================================================================

echo ""
yellow "═══ Path 2: Hard rejection at gateway  SUBMITTED → REJECTED ═══"
ID=$(create_instance "$ORDER_CREATE_QQQ")
echo "  Instance id: ${ID}"

trigger "$ID" "SUBMIT"      "$ORDER_CREATE_QQQ"   "SUBMITTED"
trigger "$ID" "REJECT_HARD" "$REJECT_HARD_PAYLOAD" "REJECTED"

# =============================================================================
# Path 3: Soft rejection → amendment → resubmit → happy path
# NEW → SUBMITTED → AMENDABLE → SUBMITTED → VALIDATED → ... → SETTLED
# =============================================================================

echo ""
yellow "═══ Path 3: Soft reject → amend & resubmit → settled ═══"
ID=$(create_instance "$ORDER_REDEEM_IWM")
echo "  Instance id: ${ID}"

trigger "$ID" "SUBMIT"              "$ORDER_REDEEM_IWM"      "SUBMITTED"
trigger "$ID" "REJECT_SOFT"         "$REJECT_SOFT_PAYLOAD"   "AMENDABLE"
trigger "$ID" "AMEND_RESUBMIT"      "$AMEND_RESUBMIT_PAYLOAD" "SUBMITTED"
trigger "$ID" "PASS_VALIDATION"     "$PASS_VALIDATION"       "VALIDATED"
trigger "$ID" "AFFIRM"              "$AFFIRM"                "AFFIRMED"
trigger "$ID" "PRICE"               "$PRICE"                 "PRICED"
trigger "$ID" "GENERATE_SETTLEMENT" "$GEN_SETTLEMENT"        "SETTLING"
trigger "$ID" "CONFIRM_SETTLEMENT"  "$CONFIRM_SETTLE"        "SETTLED"

# =============================================================================
# Path 4: Soft rejection → abandon
# NEW → SUBMITTED → AMENDABLE → CANCELLED
# =============================================================================

echo ""
yellow "═══ Path 4: Soft reject → abandon ═══"
ID=$(create_instance "$ORDER_CREATE_VOO")
echo "  Instance id: ${ID}"

trigger "$ID" "SUBMIT"      "$ORDER_CREATE_VOO"     "SUBMITTED"
trigger "$ID" "REJECT_SOFT" "$REJECT_SOFT_PAYLOAD"  "AMENDABLE"
trigger "$ID" "ABANDON"     "$CANCEL_PAYLOAD"       "CANCELLED"

# =============================================================================
# Path 5: Issuer rejection from VALIDATED
# NEW → SUBMITTED → VALIDATED → REJECTED
# =============================================================================

echo ""
yellow "═══ Path 5: Issuer rejects after validation  VALIDATED → REJECTED ═══"
ID=$(create_instance "$ORDER_REDEEM_TLT")
echo "  Instance id: ${ID}"

trigger "$ID" "SUBMIT"          "$ORDER_REDEEM_TLT"  "SUBMITTED"
trigger "$ID" "PASS_VALIDATION" "$PASS_VALIDATION"   "VALIDATED"
trigger "$ID" "REJECT"          "$REJECT_PAYLOAD"    "REJECTED"

# =============================================================================
# Path 6: Cancel from VALIDATED
# NEW → SUBMITTED → VALIDATED → CANCELLED
# =============================================================================

echo ""
yellow "═══ Path 6: Cancel from VALIDATED ═══"
ID=$(create_instance "$ORDER_CREATE_XLF")
echo "  Instance id: ${ID}"

trigger "$ID" "SUBMIT"          "$ORDER_CREATE_XLF"  "SUBMITTED"
trigger "$ID" "PASS_VALIDATION" "$PASS_VALIDATION"   "VALIDATED"
trigger "$ID" "CANCEL"          "$CANCEL_PAYLOAD"    "CANCELLED"

# =============================================================================
# Path 7: Cancel from AFFIRMED
# NEW → SUBMITTED → VALIDATED → AFFIRMED → CANCELLED
# =============================================================================

echo ""
yellow "═══ Path 7: Cancel from AFFIRMED ═══"
ID=$(create_instance "$ORDER_CREATE_GLD")
echo "  Instance id: ${ID}"

trigger "$ID" "SUBMIT"          "$ORDER_CREATE_GLD"  "SUBMITTED"
trigger "$ID" "PASS_VALIDATION" "$PASS_VALIDATION"   "VALIDATED"
trigger "$ID" "AFFIRM"          "$AFFIRM"            "AFFIRMED"
trigger "$ID" "CANCEL"          "$CANCEL_PAYLOAD"    "CANCELLED"

# =============================================================================
# Path 8: Settlement failure → ops retry → settled
# ... → SETTLING → OPS_REVIEW → SETTLING → SETTLED
# =============================================================================

echo ""
yellow "═══ Path 8: Settlement failure → ops retry → settled ═══"
ID=$(create_instance "$ORDER_REDEEM_EEM")
echo "  Instance id: ${ID}"

trigger "$ID" "SUBMIT"              "$ORDER_REDEEM_EEM"         "SUBMITTED"
trigger "$ID" "PASS_VALIDATION"     "$PASS_VALIDATION"          "VALIDATED"
trigger "$ID" "AFFIRM"              "$AFFIRM"                   "AFFIRMED"
trigger "$ID" "PRICE"               "$PRICE"                    "PRICED"
trigger "$ID" "GENERATE_SETTLEMENT" "$GEN_SETTLEMENT"           "SETTLING"
trigger "$ID" "SETTLEMENT_FAIL"     "$SETTLEMENT_FAIL_PAYLOAD"  "OPS_REVIEW"
trigger "$ID" "RETRY_SETTLEMENT"    '{}'                        "SETTLING"
trigger "$ID" "CONFIRM_SETTLEMENT"  "$CONFIRM_SETTLE"           "SETTLED"

# =============================================================================
# Path 9: Settlement failure → escalate cancel
# ... → SETTLING → OPS_REVIEW → CANCELLED
# =============================================================================

echo ""
yellow "═══ Path 9: Settlement failure → escalate cancel ═══"
ID=$(create_instance "$ORDER_CREATE_HYG")
echo "  Instance id: ${ID}"

trigger "$ID" "SUBMIT"              "$ORDER_CREATE_HYG"         "SUBMITTED"
trigger "$ID" "PASS_VALIDATION"     "$PASS_VALIDATION"          "VALIDATED"
trigger "$ID" "AFFIRM"              "$AFFIRM"                   "AFFIRMED"
trigger "$ID" "PRICE"               "$PRICE"                    "PRICED"
trigger "$ID" "GENERATE_SETTLEMENT" "$GEN_SETTLEMENT"           "SETTLING"
trigger "$ID" "SETTLEMENT_FAIL"     "$SETTLEMENT_FAIL_PAYLOAD"  "OPS_REVIEW"
trigger "$ID" "ESCALATE_CANCEL"     "$CANCEL_PAYLOAD"           "CANCELLED"

# =============================================================================
# Blotter population: leave some orders in intermediate states
# =============================================================================

echo ""
yellow "═══ Blotter population: orders in various in-progress states ═══"

# Order stuck in SUBMITTED (awaiting validation)
ID=$(create_instance "$ORDER_CREATE_VTI")
echo "  Instance id: ${ID} — leaving in SUBMITTED"
trigger "$ID" "SUBMIT" "$ORDER_CREATE_VTI" "SUBMITTED"

# Order in VALIDATED (awaiting issuer decision)
ORDER_CREATE_SPY2='{"action":"CREATE","ticker":"SPY","units":350,"unit_size":50000,"method":"Cash","basket_type":"Standard"}'
ID=$(create_instance "$ORDER_CREATE_SPY2")
echo "  Instance id: ${ID} — leaving in VALIDATED"
trigger "$ID" "SUBMIT"          "$ORDER_CREATE_SPY2" "SUBMITTED"
trigger "$ID" "PASS_VALIDATION" "$PASS_VALIDATION"   "VALIDATED"

# Order in AFFIRMED (awaiting NAV strike)
ORDER_REDEEM_QQQ='{"action":"REDEEM","ticker":"QQQ","units":100,"unit_size":50000,"method":"Cash","basket_type":"Standard"}'
ID=$(create_instance "$ORDER_REDEEM_QQQ")
echo "  Instance id: ${ID} — leaving in AFFIRMED"
trigger "$ID" "SUBMIT"          "$ORDER_REDEEM_QQQ"  "SUBMITTED"
trigger "$ID" "PASS_VALIDATION" "$PASS_VALIDATION"   "VALIDATED"
trigger "$ID" "AFFIRM"          "$AFFIRM"            "AFFIRMED"

# Order in PRICED (awaiting settlement generation)
ORDER_CREATE_IWM='{"action":"CREATE","ticker":"IWM","units":450,"unit_size":25000,"method":"In-Kind","basket_type":"Custom"}'
ID=$(create_instance "$ORDER_CREATE_IWM")
echo "  Instance id: ${ID} — leaving in PRICED"
trigger "$ID" "SUBMIT"          "$ORDER_CREATE_IWM"  "SUBMITTED"
trigger "$ID" "PASS_VALIDATION" "$PASS_VALIDATION"   "VALIDATED"
trigger "$ID" "AFFIRM"          "$AFFIRM"            "AFFIRMED"
trigger "$ID" "PRICE"           "$PRICE"             "PRICED"

# Order in SETTLING (awaiting settlement confirmation)
ORDER_CREATE_VOO2='{"action":"CREATE","ticker":"VOO","units":275,"unit_size":50000,"method":"Cash","basket_type":"Standard"}'
ID=$(create_instance "$ORDER_CREATE_VOO2")
echo "  Instance id: ${ID} — leaving in SETTLING"
trigger "$ID" "SUBMIT"              "$ORDER_CREATE_VOO2" "SUBMITTED"
trigger "$ID" "PASS_VALIDATION"     "$PASS_VALIDATION"   "VALIDATED"
trigger "$ID" "AFFIRM"              "$AFFIRM"            "AFFIRMED"
trigger "$ID" "PRICE"               "$PRICE"             "PRICED"
trigger "$ID" "GENERATE_SETTLEMENT" "$GEN_SETTLEMENT"    "SETTLING"

# Order in OPS_REVIEW (settlement failed, awaiting manual intervention)
ORDER_REDEEM_GLD='{"action":"REDEEM","ticker":"GLD","units":500,"unit_size":50000,"method":"Cash","basket_type":"Standard"}'
ID=$(create_instance "$ORDER_REDEEM_GLD")
echo "  Instance id: ${ID} — leaving in OPS_REVIEW"
trigger "$ID" "SUBMIT"              "$ORDER_REDEEM_GLD"         "SUBMITTED"
trigger "$ID" "PASS_VALIDATION"     "$PASS_VALIDATION"          "VALIDATED"
trigger "$ID" "AFFIRM"              "$AFFIRM"                   "AFFIRMED"
trigger "$ID" "PRICE"               "$PRICE"                    "PRICED"
trigger "$ID" "GENERATE_SETTLEMENT" "$GEN_SETTLEMENT"           "SETTLING"
trigger "$ID" "SETTLEMENT_FAIL"     "$SETTLEMENT_FAIL_PAYLOAD"  "OPS_REVIEW"

# Order in AMENDABLE (soft rejected, awaiting amendment)
ORDER_CREATE_TLT='{"action":"CREATE","ticker":"TLT","units":125,"unit_size":50000,"method":"Cash","basket_type":"Standard"}'
ID=$(create_instance "$ORDER_CREATE_TLT")
echo "  Instance id: ${ID} — leaving in AMENDABLE"
trigger "$ID" "SUBMIT"      "$ORDER_CREATE_TLT"    "SUBMITTED"
trigger "$ID" "REJECT_SOFT" "$REJECT_SOFT_PAYLOAD" "AMENDABLE"

# =============================================================================
# Negative tests
# =============================================================================

echo ""
yellow "═══ Negative tests ═══"

# Missing required field on SUBMIT (no units)
ID=$(create_instance '{"action":"CREATE","ticker":"SPY"}')
echo "  Instance id: ${ID}"
trigger_fail "$ID" "SUBMIT" '{
  "action": "CREATE",
  "ticker": "SPY"
}' "required"

# Invalid transition: cannot CONFIRM_SETTLEMENT from NEW
ID=$(create_instance '{"action":"CREATE","ticker":"SPY"}')
echo "  Instance id: ${ID}"
trigger_fail "$ID" "CONFIRM_SETTLEMENT" "$CONFIRM_SETTLE" "Invalid transition"

# Invalid transition: cannot AFFIRM from SUBMITTED (must validate first)
ID=$(create_instance "$ORDER_CREATE_SPY")
trigger "$ID" "SUBMIT" "$ORDER_CREATE_SPY" "SUBMITTED"
trigger_fail "$ID" "AFFIRM" "$AFFIRM" "Invalid transition"

# Invalid transition: cannot PRICE from VALIDATED (must affirm first)
ID=$(create_instance "$ORDER_CREATE_SPY")
trigger "$ID" "SUBMIT"          "$ORDER_CREATE_SPY" "SUBMITTED"
trigger "$ID" "PASS_VALIDATION" "$PASS_VALIDATION"  "VALIDATED"
trigger_fail "$ID" "PRICE" "$PRICE" "Invalid transition"

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
green "  PASS: ${PASS}"
if [ "$FAIL" -gt 0 ]; then
  red "  FAIL: ${FAIL}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
else
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
fi
