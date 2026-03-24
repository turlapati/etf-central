"""End-to-end tests for the ETF C/R order lifecycle."""
from tests.conftest import ORDER_CTX


def _create_and_submit(client):
    """Helper: create instance + auto-submit."""
    resp = client.post("/api/state-machines/instances", json={
        "workflow_name": "etf_order",
        "context": ORDER_CTX,
    })
    assert resp.status_code == 200, resp.text
    iid = resp.json()["id"]
    assert resp.json()["current_state"] == "NEW"

    resp = client.post(f"/api/etf_order/{iid}/SUBMIT", json=ORDER_CTX)
    assert resp.status_code == 200, resp.text
    assert resp.json()["new_state"] == "SUBMITTED"
    return iid


def test_full_happy_path(client, seeded_workflow):
    """NEW → SUBMITTED → VALIDATED → AFFIRMED → PRICED → SETTLING → SETTLED"""
    iid = _create_and_submit(client)

    # PASS_VALIDATION: SUBMITTED → VALIDATED
    resp = client.post(f"/api/etf_order/{iid}/PASS_VALIDATION", json={})
    assert resp.json()["new_state"] == "VALIDATED"

    # AFFIRM: VALIDATED → AFFIRMED
    resp = client.post(f"/api/etf_order/{iid}/AFFIRM", json={"affirmed_by": "issuer_desk"})
    assert resp.json()["new_state"] == "AFFIRMED"

    # PRICE: AFFIRMED → PRICED
    resp = client.post(f"/api/etf_order/{iid}/PRICE", json={
        "nav_per_unit": 571.82,
        "net_settlement_amount": 57182000,
    })
    assert resp.json()["new_state"] == "PRICED"

    # GENERATE_SETTLEMENT: PRICED → SETTLING
    resp = client.post(f"/api/etf_order/{iid}/GENERATE_SETTLEMENT", json={
        "dtc_instruction_id": "DTC-001",
    })
    assert resp.json()["new_state"] == "SETTLING"

    # CONFIRM_SETTLEMENT: SETTLING → SETTLED
    resp = client.post(f"/api/etf_order/{iid}/CONFIRM_SETTLEMENT", json={
        "settlement_ref": "SREF-001",
        "depository": "DTC",
    })
    assert resp.json()["new_state"] == "SETTLED"

    # Verify terminal state
    resp = client.get(f"/api/state-machines/instances/{iid}")
    assert resp.json()["current_state"] == "SETTLED"


def test_hard_rejection(client, seeded_workflow):
    """NEW → SUBMITTED → REJECTED (fatal validation failure)"""
    iid = _create_and_submit(client)

    resp = client.post(f"/api/etf_order/{iid}/REJECT_HARD", json={
        "reject_reason": "Invalid AP credentials",
    })
    assert resp.status_code == 200
    assert resp.json()["new_state"] == "REJECTED"


def test_issuer_rejection(client, seeded_workflow):
    """NEW → SUBMITTED → VALIDATED → REJECTED (issuer rejects)"""
    iid = _create_and_submit(client)
    client.post(f"/api/etf_order/{iid}/PASS_VALIDATION", json={})

    resp = client.post(f"/api/etf_order/{iid}/REJECT", json={
        "reject_reason": "Inventory shortage",
    })
    assert resp.status_code == 200
    assert resp.json()["new_state"] == "REJECTED"


def test_amendment_loop(client, seeded_workflow):
    """NEW → SUBMITTED → AMENDABLE → SUBMITTED → VALIDATED (soft reject then fix)"""
    iid = _create_and_submit(client)

    # Soft reject
    resp = client.post(f"/api/etf_order/{iid}/REJECT_SOFT", json={
        "amendment_reason": "Unit size below minimum",
    })
    assert resp.json()["new_state"] == "AMENDABLE"

    # Amend and resubmit
    resp = client.post(f"/api/etf_order/{iid}/AMEND_RESUBMIT", json={
        "units": 5,
        "unit_size": 50000,
    })
    assert resp.json()["new_state"] == "SUBMITTED"

    # Now pass validation
    resp = client.post(f"/api/etf_order/{iid}/PASS_VALIDATION", json={})
    assert resp.json()["new_state"] == "VALIDATED"


def test_amendment_abandon(client, seeded_workflow):
    """AMENDABLE → CANCELLED (AP gives up)"""
    iid = _create_and_submit(client)
    client.post(f"/api/etf_order/{iid}/REJECT_SOFT", json={})

    resp = client.post(f"/api/etf_order/{iid}/ABANDON", json={
        "cancel_reason": "No longer needed",
    })
    assert resp.status_code == 200
    assert resp.json()["new_state"] == "CANCELLED"


def test_settlement_failure_and_retry(client, seeded_workflow):
    """SETTLING → OPS_REVIEW → SETTLING → SETTLED"""
    iid = _create_and_submit(client)
    client.post(f"/api/etf_order/{iid}/PASS_VALIDATION", json={})
    client.post(f"/api/etf_order/{iid}/AFFIRM", json={})
    client.post(f"/api/etf_order/{iid}/PRICE", json={})
    client.post(f"/api/etf_order/{iid}/GENERATE_SETTLEMENT", json={})

    # Settlement fails
    resp = client.post(f"/api/etf_order/{iid}/SETTLEMENT_FAIL", json={
        "fail_reason": "Counterparty can't deliver basket",
        "fail_type": "COUNTERPARTY_FAIL",
    })
    assert resp.json()["new_state"] == "OPS_REVIEW"

    # Retry
    resp = client.post(f"/api/etf_order/{iid}/RETRY_SETTLEMENT", json={})
    assert resp.json()["new_state"] == "SETTLING"

    # Now succeeds
    resp = client.post(f"/api/etf_order/{iid}/CONFIRM_SETTLEMENT", json={})
    assert resp.json()["new_state"] == "SETTLED"


def test_settlement_failure_escalate_cancel(client, seeded_workflow):
    """OPS_REVIEW → CANCELLED (give up after settlement fail)"""
    iid = _create_and_submit(client)
    client.post(f"/api/etf_order/{iid}/PASS_VALIDATION", json={})
    client.post(f"/api/etf_order/{iid}/AFFIRM", json={})
    client.post(f"/api/etf_order/{iid}/PRICE", json={})
    client.post(f"/api/etf_order/{iid}/GENERATE_SETTLEMENT", json={})
    client.post(f"/api/etf_order/{iid}/SETTLEMENT_FAIL", json={})

    resp = client.post(f"/api/etf_order/{iid}/ESCALATE_CANCEL", json={
        "cancel_reason": "Unrecoverable settlement failure",
    })
    assert resp.status_code == 200
    assert resp.json()["new_state"] == "CANCELLED"


def test_cancel_from_validated(client, seeded_workflow):
    """VALIDATED → CANCELLED (cancel before affirmation)"""
    iid = _create_and_submit(client)
    client.post(f"/api/etf_order/{iid}/PASS_VALIDATION", json={})

    resp = client.post(f"/api/etf_order/{iid}/CANCEL", json={
        "cancel_reason": "AP withdrew request",
    })
    assert resp.status_code == 200
    assert resp.json()["new_state"] == "CANCELLED"


def test_cancel_from_affirmed(client, seeded_workflow):
    """AFFIRMED → CANCELLED (cancel before NAV pricing)"""
    iid = _create_and_submit(client)
    client.post(f"/api/etf_order/{iid}/PASS_VALIDATION", json={})
    client.post(f"/api/etf_order/{iid}/AFFIRM", json={})

    resp = client.post(f"/api/etf_order/{iid}/CANCEL", json={
        "cancel_reason": "Market conditions changed",
    })
    assert resp.status_code == 200
    assert resp.json()["new_state"] == "CANCELLED"


def test_invalid_trigger_returns_409(client, seeded_workflow):
    """Firing AFFIRM on a NEW order (wrong state) should fail."""
    resp = client.post("/api/state-machines/instances", json={
        "workflow_name": "etf_order",
        "context": ORDER_CTX,
    })
    iid = resp.json()["id"]

    resp = client.post(f"/api/etf_order/{iid}/AFFIRM", json={})
    assert resp.status_code == 409


def test_transition_history(client, seeded_workflow):
    """Verify transition log is populated after state changes."""
    iid = _create_and_submit(client)
    client.post(f"/api/etf_order/{iid}/PASS_VALIDATION", json={})
    client.post(f"/api/etf_order/{iid}/AFFIRM", json={})

    resp = client.get(f"/api/state-machines/instances/{iid}/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 3
    states = [h["to_state"] for h in history]
    assert "SUBMITTED" in states
    assert "VALIDATED" in states
    assert "AFFIRMED" in states
