# ETF Central

An institutional-grade trading terminal for managing ETF creation and redemption orders. Built as a full-stack application with a React frontend and a Mermaid-driven workflow engine backend.

## Architecture

```
etf-central/
├── backend/          Python/FastAPI workflow engine (port 8000)
├── frontend/         React/TypeScript trading terminal (port 5173)
├── scripts/          Startup and seed scripts
└── docs/             Design docs and guides
```

**Backend** — A state machine engine that generates REST APIs from Mermaid statechart diagrams. Workflow definitions describe states, transitions, triggers, guards, and actions. The engine dynamically creates typed API endpoints for each trigger, persists instance state in SQLite, and maintains a full audit log of transitions.

**Frontend** — A single-page trading terminal built with React, TypeScript, and Tailwind CSS. Features an order entry form, live order blotter with 3-second polling, market color charts (Premium/Discount, Short Interest, Spread & Volume, Shares Outstanding via Recharts), positions panel, and full order lifecycle management through workflow actions.

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

### One-command startup

```bash
bash scripts/start.sh
```

This will:
1. Create a Python venv and install backend dependencies
2. Start the backend on port 8000 (auto-seeds the ETF order workflow on first run)
3. Install npm packages and start the frontend on port 5173

### Manual startup

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
python main.py
```

The ETF order workflow auto-seeds on first startup. To re-seed manually:
```bash
bash scripts/seed-etf-workflow.sh
```

**Run the end-to-end test (exercises all state machine paths):**
```bash
bash scripts/etf-workflow-test.sh
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** to use the trading terminal.
Open **http://localhost:8000/docs** to browse the API.

## ETF Order Workflow

Models the real-world ETF Creation/Redemption lifecycle — from AP order submission through gateway validation, issuer affirmation, end-of-day NAV pricing, and DTC/NSCC settlement.

```
NEW → SUBMITTED → VALIDATED → AFFIRMED → PRICED → SETTLING → SETTLED
         │            │           │                    │
     REJECT_SOFT    REJECT      CANCEL            SETTLE_FAIL
         ↓            ↓           ↓                    ↓
     AMENDABLE     REJECTED   CANCELLED           OPS_REVIEW
      ↙     ↘                                     ↙      ↘
  RESUBMIT  ABANDON                           RETRY   ESCALATE
      ↓        ↓                                ↓         ↓
  SUBMITTED CANCELLED                       SETTLING  CANCELLED
```

| Trigger | From → To | Payload |
|---------|----------|---------|
| CREATE | [*] → NEW | action, ticker, units, unit_size, method, basket_type |
| SUBMIT | NEW → SUBMITTED | (same as create — auto-fired) |
| PASS_VALIDATION | SUBMITTED → VALIDATED | validation_id, checks_passed |
| REJECT_SOFT | SUBMITTED → AMENDABLE | amendment_reason |
| REJECT_HARD | SUBMITTED → REJECTED | reject_reason |
| AFFIRM | VALIDATED → AFFIRMED | affirmed_by, estimated_cash_amount |
| REJECT | VALIDATED → REJECTED | reject_reason |
| PRICE | AFFIRMED → PRICED | nav_per_unit, net_settlement_amount |
| GENERATE_SETTLEMENT | PRICED → SETTLING | dtc_instruction_id |
| CONFIRM_SETTLEMENT | SETTLING → SETTLED | settlement_ref, depository |
| SETTLEMENT_FAIL | SETTLING → OPS_REVIEW | fail_reason, fail_type |
| RETRY_SETTLEMENT | OPS_REVIEW → SETTLING | — |
| ESCALATE_CANCEL | OPS_REVIEW → CANCELLED | cancel_reason |
| AMEND_RESUBMIT | AMENDABLE → SUBMITTED | amended_fields |
| ABANDON | AMENDABLE → CANCELLED | cancel_reason |
| CANCEL | VALIDATED/AFFIRMED → CANCELLED | cancel_reason |

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 19, TypeScript, Vite | SPA framework |
| Styling | Tailwind CSS v4 | Design system |
| Charts | Recharts | Market data visualization |
| State mgmt | TanStack React Query | Server state, polling, caching |
| Backend | FastAPI, Python 3.10+ | REST API framework |
| ORM | SQLModel (SQLAlchemy + Pydantic) | Database + validation |
| Database | SQLite | Zero-config persistence |
| Engine | Mermaid parser → dynamic routes | Workflow state machine |

## Project Structure

```
backend/
├── main.py                          Entry point
├── app/
│   ├── main.py                      FastAPI app factory
│   ├── config.py                    Settings (env-based)
│   ├── database.py                  SQLite/SQLModel setup
│   ├── models.py                    Database models
│   ├── engine.py                    Mermaid parser + state machine
│   ├── trigger_router.py            Dynamic route generation
│   ├── trigger_engine.py            Trigger execution orchestrator
│   ├── guards.py                    Guard expression evaluator
│   ├── middleware.py                Correlation ID middleware
│   ├── registry.py                  Action decorator registry
│   ├── action_loader.py             Action discovery + DB sync
│   ├── seed.py                      Auto-seed ETF order workflow
│   ├── api/
│   │   ├── state_machines_api.py    Workflow CRUD endpoints
│   │   └── instances.py             Instance management endpoints
│   ├── actions/                     Built-in action library
│   ├── schemas/                     Payload validation
│   └── services/                    Async tasks, metadata extraction
│
frontend/
├── index.html
├── vite.config.ts                   Tailwind plugin + API proxy
├── src/
│   ├── App.tsx                      Root component
│   ├── api/                         Fetch client + typed API calls
│   ├── hooks/                       React Query hooks
│   ├── components/                  UI components
│   ├── data/                        Mock positions + market data
│   └── lib/                         Formatters + constants
```

## License

Internal use.
