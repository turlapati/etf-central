"""Tests for instance CRUD endpoints."""
from tests.conftest import ORDER_CTX


def test_create_instance(client, seeded_workflow):
    resp = client.post("/api/state-machines/instances", json={
        "workflow_name": "etf_order",
        "context": ORDER_CTX,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow_name"] == "etf_order"
    assert data["current_state"] == "NEW"
    assert data["context"]["ticker"] == "SPY"


def test_list_instances_filter_by_workflow(client, seeded_workflow):
    client.post("/api/state-machines/instances", json={
        "workflow_name": "etf_order",
        "context": ORDER_CTX,
    })
    resp = client.get("/api/state-machines/instances?workflow_name=etf_order")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all(i["workflow_name"] == "etf_order" for i in data)


def test_get_instance_detail(client, seeded_workflow):
    create = client.post("/api/state-machines/instances", json={
        "workflow_name": "etf_order",
        "context": {**ORDER_CTX, "action": "REDEEM", "ticker": "HYG"},
    })
    instance_id = create.json()["id"]

    resp = client.get(f"/api/state-machines/instances/{instance_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "available_events" in data
    assert data["context"]["ticker"] == "HYG"


def test_get_nonexistent_instance_returns_404(client):
    resp = client.get("/api/state-machines/instances/99999")
    assert resp.status_code == 404
