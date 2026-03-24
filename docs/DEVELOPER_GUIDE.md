# Developer Guide: Supporting New State Machines

This guide explains how to add a new state machine workflow, evolve an existing one with versioning, and what parts of the codebase are affected.

## Architecture Overview

The system uses a **data-driven state machine** architecture. Workflows are defined in Mermaid syntax and stored in the database. The backend dynamically generates API routes from those definitions, and the frontend dynamically renders action buttons and forms from API responses.

```
Mermaid Definition
  → Seeded into the database once (via seed script, API, or first-run auto-seed)
  → On every startup, backend reads definitions from DB
  → Dynamic API routes generated from DB definitions: POST /api/{workflow}/{id}/{TRIGGER}
  → Frontend receives available_triggers with payload_schema per instance
  → UI renders buttons and forms dynamically
```

**Important:** The backend does NOT re-seed on every startup. The auto-seed in `main.py` only runs if no definition exists yet in the database (first run). After that, the **database is the source of truth**.

## Versioning Model

The backend supports **versioned workflow definitions**. This is central to how changes are managed.

### How it works

- Multiple definition rows can share the same `name` (e.g., `"etf_order"`) with different `version` numbers.
- Only one version per workflow name is marked `is_active = True` at a time.
- Each instance stores a `definition_id` — a **permanent binding** to the exact definition version it was created under.
- New instances are created against the currently active version. Existing instances continue operating under their original version.

### Instance-version binding

When an instance is created (via `POST /api/state-machines/instances`), the backend resolves the active definition for the given `workflow_name` and stores that `definition_id` on the instance. From that point on:

- `GET /api/state-machines/instances/{id}` returns the **bound version's** Mermaid diagram and available triggers
- `POST /api/{workflow}/{id}/{TRIGGER}` validates the transition against the **bound version's** state machine
- Guards, actions, and payload schemas are all resolved from the **bound version's** `TransitionMetadata`

There is no automatic migration — a v1 instance remains on v1 forever, even after v2 is deployed.

### Trigger route stability

`TriggerRouteGenerator` unions triggers across **all versions** of a workflow name to produce stable API routes. This means:

- Adding a trigger in v2 creates a new route that works for v2 instances
- Removing a trigger in v2 does NOT break the route — v1 instances can still fire it
- The route `POST /api/etf_order/{id}/AFFIRM` exists as long as any version defines it

The backend resolves version-correctness at execution time, not at routing time.

### Example: v1 instance after v2 deployment

| Operation | v1 instance (VALIDATED) | New v2 instance (VALIDATED) |
|---|---|---|
| GET available_triggers | `[AFFIRM, REJECT, CANCEL]` (v1 diagram) | `[REVIEW, REJECT, CANCEL]` (v2 diagram) |
| POST .../AFFIRM | Works (v1 has this transition) | Fails (v2 removed it) |
| POST .../REVIEW | Fails (v1 doesn't have it) | Works (v2 added it) |

### Creating a new version

Use the versioning API endpoint:

```
POST /api/state-machines/definitions/{definition_id}/versions
```

```json
{
  "mermaid_definition": "stateDiagram-v2\n  ...",
  "initial_state": "NEW",
  "description": "Added COMPLIANCE_HOLD between VALIDATED and AFFIRMED",
  "change_log": "Inserted compliance review step per regulatory requirement"
}
```

This will:
1. Deactivate the old version (`is_active = False`)
2. Create a new row with `version = old + 1`, `is_active = True`, `parent_version_id = old.id`
3. Populate `TransitionMetadata` from the new Mermaid diagram
4. Reload trigger routes (call `POST /admin/reload-routes` after)

Existing instances are unaffected. Only new instances will use the new version.

## What Changes Where

| Change type | Backend / DB | `constants.ts` | `OrderDetailPanel.tsx` | Other UI |
|---|---|---|---|---|
| Add/remove a state | New version via API | Add display label + color | No | No |
| Add/remove a transition | New version via API | No | Add trigger label + color | No |
| Add/remove payload fields | New version via API | No | No | No |
| Rename a state | New version via API | Update key | No | No |
| Rename a trigger | New version via API | No | Update key | No |
| Brand new workflow | Seed script or API | Add state entries | Add trigger entries | New blotter + entry form |

## Modifying the Existing ETF Order Workflow

### Step 1: Prepare the updated Mermaid definition

Start from the current definition. You can retrieve it from the database or copy from:

- `scripts/seed-etf-workflow.sh` — the seed script (canonical reference for the initial version)
- `backend/app/seed.py` — first-run fallback (keep in sync for fresh deployments)

Edit the Mermaid to add/remove states and transitions. Example — adding a `COMPLIANCE_HOLD` state:

```mermaid
state COMPLIANCE_HOLD

VALIDATED --> COMPLIANCE_HOLD : COMPLIANCE_FLAG
COMPLIANCE_HOLD --> VALIDATED : COMPLIANCE_CLEAR
COMPLIANCE_HOLD --> REJECTED : COMPLIANCE_REJECT
```

Add payload schemas via `note` blocks to drive form generation:

```mermaid
note right of COMPLIANCE_HOLD
    trigger_type: api
    description: "Order flagged for compliance review"
    payload:
        flag_reason: string, optional
        flagged_by: string, optional
end note
```

### Step 2: Create a new version

Push the updated definition as a new version via the API:

```bash
curl -X POST http://localhost:8000/api/state-machines/definitions/{DEFINITION_ID}/versions \
  -H "Content-Type: application/json" \
  -d '{
    "mermaid_definition": "stateDiagram-v2\n  ...",
    "initial_state": "NEW",
    "description": "Added compliance hold step",
    "change_log": "Inserted COMPLIANCE_HOLD between VALIDATED and AFFIRMED"
  }'

# Reload trigger routes to pick up new triggers
curl -X POST http://localhost:8000/admin/reload-routes
```

After this:
- The old version is deactivated; new instances use the new version
- Existing in-flight instances continue on the old version unchanged

### Step 3: Update frontend display mappings

**`frontend/src/lib/constants.ts`** — add entries for new states:

```ts
COMPLIANCE_HOLD: { label: "HOLD", color: "text-yellow-400" },
```

**`frontend/src/components/OrderDetailPanel.tsx`** — add entries in `TRIGGER_LABELS` for new triggers:

```ts
COMPLIANCE_FLAG:   { label: "Flag Compliance",   color: "bg-yellow-500/20 text-yellow-400" },
COMPLIANCE_CLEAR:  { label: "Clear Compliance",   color: "bg-accent-green text-bg-main" },
COMPLIANCE_REJECT: { label: "Reject (Compliance)", color: "bg-accent-red text-white" },
```

### Step 4: Keep seed files in sync

Update `scripts/seed-etf-workflow.sh` and `backend/app/seed.py` to reflect the latest definition. These are used for fresh deployments (empty database), not for upgrading existing ones.

### What you do NOT need to change

- **Trigger buttons** — rendered dynamically from `available_events` in the API response
- **Payload forms** — built on-the-fly from `payload_schema` JSON schema returned by the API
- **History panel** — displays whatever transitions the API returns
- **StatusBadge component** — falls back to raw state name if no `STATE_DISPLAY` entry exists (but add one for polish)
- **Backend route registration** — `TriggerRouteGenerator` auto-creates routes for every transition across all versions

## Adding a Brand New Workflow

### Step 1: Write the Mermaid definition

Use `docs/reference_statemachines/mermaid-state-machine-guide.md` as a syntax reference. Create a new reference doc in `docs/reference_statemachines/` for the design.

### Step 2: Create a seed function

Add a new file or extend `backend/app/seed.py`:

```python
TRADE_ORDER_MERMAID = """\
stateDiagram-v2
    [*] --> BOOKED : BOOK
    BOOKED --> VALIDATED : VALIDATE
    ...
"""

def seed_trade_workflow(session: Session) -> StateMachineDefinition:
    parser = MermaidParser(TRADE_ORDER_MERMAID)
    definition = StateMachineDefinition(
        name="trade_order",          # this becomes the URL prefix
        mermaid_definition=TRADE_ORDER_MERMAID,
        initial_state=parser.initial_state or "BOOKED",
        description="Trade order lifecycle",
        version=1,
        is_active=True,
        created_by="auto-seed",
    )
    session.add(definition)
    session.commit()
    session.refresh(definition)
    populate_transition_metadata(session, definition)
    return definition
```

Then either:
- Add a similar `if not existing` guard in `main.py` lifespan for first-run auto-seed, or
- Create a dedicated seed script (like `scripts/seed-etf-workflow.sh`) and run it manually

### Step 3: Create the frontend API layer

Add a new API module similar to `frontend/src/api/etfOrders.ts`:

```ts
// frontend/src/api/tradeOrders.ts

export async function createTradeOrder(context: Record<string, any>) {
  return apiFetch<InstanceResponse>("/api/state-machines/instances", {
    method: "POST",
    body: JSON.stringify({ workflow_name: "trade_order", context }),
  });
}

export async function listTradeOrders() {
  return apiFetch<InstanceResponse[]>(
    "/api/state-machines/instances?workflow_name=trade_order&limit=100"
  );
}

export async function fireTradeOrderTrigger(id: number, trigger: string, payload = {}) {
  return apiFetch<TriggerResponse>(`/api/trade_order/${id}/${trigger}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

Note: `getOrder` and `getHistory` use instance ID and are workflow-agnostic — they can be reused.

### Step 4: Add frontend display mappings

Add state display entries and trigger labels for all states and triggers in the new workflow. The existing `STATE_DISPLAY` and `TRIGGER_LABELS` maps are shared across workflows — keys just need to be unique.

### Step 5: Build the UI (if needed)

The existing `OrderDetailPanel` component is largely workflow-agnostic:
- StatusBadge, trigger buttons, payload forms, and history all render from API data
- The `OrderBlotter` and `OrderEntryPanel` are ETF-specific (they reference `ctx.ticker`, `ctx.action`, etc.)

For a new workflow you will need:
- A new blotter component with columns appropriate to that workflow's context fields
- A new entry form matching the CREATE trigger's payload schema
- The detail panel can potentially be reused or lightly adapted

## Frontend Version Considerations

The frontend is largely version-unaware by design:

- It never references version numbers directly
- `GET /api/state-machines/instances/{id}` returns the **bound version's** `available_triggers` and `mermaid_definition`
- The UI renders whatever the API returns — v1 instances show v1 triggers, v2 instances show v2 triggers
- `fireTrigger()` calls stable routes; the backend resolves version correctness

**When adding states or triggers in a new version**, the only frontend changes needed are adding entries to `STATE_DISPLAY` and `TRIGGER_LABELS`. Keep old entries — they're still needed for in-flight instances on older versions. The UI gracefully falls back to raw names for unknown states/triggers, but display mappings give a polished experience.

## File Reference

| File | Role | Change frequency |
|---|---|---|
| `scripts/seed-etf-workflow.sh` | Seed script for fresh deployments | Keep in sync with latest version |
| `backend/app/seed.py` | First-run auto-seed fallback (skipped if DB has data) | Keep in sync with seed script |
| `backend/app/api/state_machines_api.py` | Versioning API (`POST .../versions`) | Rarely (framework code) |
| `backend/app/trigger_router.py` | Dynamic route generation (unions across versions) | Rarely (framework code) |
| `backend/app/trigger_engine.py` | Trigger execution (resolves instance's bound version) | Rarely (framework code) |
| `backend/app/engine.py` | Mermaid parser | Rarely (framework code) |
| `frontend/src/lib/constants.ts` | `STATE_DISPLAY` map | Every state add/rename |
| `frontend/src/components/OrderDetailPanel.tsx` | `TRIGGER_LABELS` map + detail UI | Every trigger add/rename |
| `frontend/src/components/StatusBadge.tsx` | Renders state label + color | Never (data-driven) |
| `frontend/src/components/OrderBlotter.tsx` | Order list table | Only for new workflows |
| `frontend/src/components/OrderEntryPanel.tsx` | Create order form | Only for new workflows |
| `frontend/src/api/etfOrders.ts` | ETF API calls | Only for new workflows |
| `frontend/src/api/types.ts` | Shared TypeScript types | Rarely |
| `docs/reference_statemachines/` | Design reference only — not used at runtime | Optional |
