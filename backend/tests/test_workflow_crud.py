"""Tests for workflow definition CRUD operations."""


def test_create_workflow(client):
    resp = client.post("/api/state-machines/definitions", json={
        "name": "test_wf",
        "mermaid_definition": "stateDiagram-v2\n    [*] --> OPEN : START\n    OPEN --> CLOSED : CLOSE",
        "initial_state": "OPEN",
        "description": "Test workflow",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test_wf"
    assert data["initial_state"] == "OPEN"
    assert data["is_active"] is True


def test_list_workflows(client):
    # Ensure at least one exists
    client.post("/api/state-machines/definitions", json={
        "name": "list_test_wf",
        "mermaid_definition": "stateDiagram-v2\n    [*] --> A : GO\n    A --> B : NEXT",
        "initial_state": "A",
    })
    resp = client.get("/api/state-machines/definitions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_get_workflow_detail(client):
    create = client.post("/api/state-machines/definitions", json={
        "name": "detail_test_wf",
        "mermaid_definition": "stateDiagram-v2\n    [*] --> X : BEGIN\n    X --> Y : END",
        "initial_state": "X",
    })
    wf_id = create.json()["id"]

    resp = client.get(f"/api/state-machines/definitions/{wf_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "detail_test_wf"
    assert "mermaid_definition" in data


def test_duplicate_workflow_name_fails(client):
    client.post("/api/state-machines/definitions", json={
        "name": "dup_test",
        "mermaid_definition": "stateDiagram-v2\n    [*] --> A : GO",
        "initial_state": "A",
    })
    resp = client.post("/api/state-machines/definitions", json={
        "name": "dup_test",
        "mermaid_definition": "stateDiagram-v2\n    [*] --> B : GO",
        "initial_state": "B",
    })
    assert resp.status_code in (400, 409)
