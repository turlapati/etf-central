import os
import sys
from pathlib import Path

# MUST set env before any app module is imported
TEST_DB = Path("./data/test.db")
for suffix in ("", "-shm", "-wal"):
    Path(str(TEST_DB) + suffix).unlink(missing_ok=True)
TEST_DB.parent.mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

import pytest
from fastapi.testclient import TestClient
from app.database import create_db_and_tables, initialize_action_system, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    create_db_and_tables()
    initialize_action_system()
    yield
    for suffix in ("", "-shm", "-wal"):
        Path(str(TEST_DB) + suffix).unlink(missing_ok=True)


@pytest.fixture()
def client():
    from app.trigger_router import get_trigger_router
    from sqlmodel import Session

    with Session(engine) as session:
        trigger_router = get_trigger_router(session)
        try:
            app.include_router(trigger_router)
        except Exception:
            pass
    return TestClient(app)


ETF_MERMAID = """stateDiagram-v2
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

    NEW --> SUBMITTED : SUBMIT
    SUBMITTED --> VALIDATED : PASS_VALIDATION
    SUBMITTED --> AMENDABLE : REJECT_SOFT
    SUBMITTED --> REJECTED : REJECT_HARD
    VALIDATED --> AFFIRMED : AFFIRM
    VALIDATED --> REJECTED : REJECT
    VALIDATED --> CANCELLED : CANCEL
    AFFIRMED --> PRICED : PRICE
    AFFIRMED --> CANCELLED : CANCEL
    PRICED --> SETTLING : GENERATE_SETTLEMENT
    SETTLING --> SETTLED : CONFIRM_SETTLEMENT
    SETTLING --> OPS_REVIEW : SETTLEMENT_FAIL
    OPS_REVIEW --> SETTLING : RETRY_SETTLEMENT
    OPS_REVIEW --> CANCELLED : ESCALATE_CANCEL
    AMENDABLE --> SUBMITTED : AMEND_RESUBMIT
    AMENDABLE --> CANCELLED : ABANDON
    SETTLED --> [*]
    REJECTED --> [*]
    CANCELLED --> [*]

    note right of NEW
        trigger_type: api
        payload:
            action: string, required [CREATE, REDEEM]
            ticker: string, required [SPY, QQQ, IWM, VOO, TLT]
            units: integer, required
            unit_size: integer, required
            method: string, required [Cash, In-Kind]
            basket_type: string, required [Standard, Custom]
    end note

    note right of REJECTED
        trigger_type: api
        payload:
            reject_reason: string, optional
    end note

    note right of CANCELLED
        trigger_type: api
        payload:
            cancel_reason: string, optional
    end note"""


ORDER_CTX = {
    "action": "CREATE",
    "ticker": "SPY",
    "units": 2,
    "unit_size": 50000,
    "method": "Cash",
    "basket_type": "Standard",
}


@pytest.fixture()
def seeded_workflow(client):
    resp = client.post("/api/state-machines/definitions", json={
        "name": "etf_order",
        "mermaid_definition": ETF_MERMAID,
        "initial_state": "NEW",
        "description": "ETF order lifecycle",
    })
    assert resp.status_code in (200, 400, 409), resp.text
    client.post("/admin/reload-routes")
    return resp.json() if resp.status_code == 200 else None
