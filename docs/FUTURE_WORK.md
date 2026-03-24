# ETF Central — Future Work

## Short-term (v1.x)

### Real-time Updates
- Replace 5-second polling with Server-Sent Events (SSE) or WebSocket push from the backend.
- Reduces latency from ~5s to <100ms for state changes.

### Live Market Data Integration
- Connect charts to a real market data feed (IEX Cloud, Polygon.io, or Bloomberg B-PIPE).
- Replace mock position prices with live quotes.
- Compute Total Value in the order form from real-time NAV.

### Order Detail Enhancements
- Inline contextual forms for triggers that require payload data (e.g., `affirmed_by`, `nav_per_unit`, `fail_reason`) — fields expand within the detail panel when a trigger is clicked, no pop-ups.
- Confirmation step before destructive actions (Reject, Cancel).
- Inline editing of order context fields.

### Security Hardening
- **CORS**: Replace wildcard `*` origin with explicit trusted origins; remove `allow_credentials` when not needed.
- **PRAGMA injection**: Replace f-string SQL in `database.py` with whitelist-validated values.
- **Admin endpoint**: Gate `/admin/reload-routes` behind authentication or API key.
- **Error sanitization**: Return generic error messages to clients; log full details server-side only.
- **Entry point**: Disable `reload=True` and bind to `127.0.0.1` in production; make configurable via env vars.
- **SQLite threading**: Address `check_same_thread=False` or migrate to PostgreSQL for concurrent workloads.
- **Payload size limit**: Add middleware to cap request body size (e.g. 1MB).
- **Email input sanitization**: Strip CRLF from subject/body in communication actions.
- **Security headers**: Add `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` middleware.

### Authentication & Authorization
- API key or JWT-based authentication.
- Role-based access: Trader (submit/view), Operations (advance lifecycle), Admin (manage workflows).
- Audit trail: associate transitions with authenticated users.

### Error Handling
- Structured error display in the UI for guard failures and payload validation errors.
- Retry logic for transient network errors.
- Optimistic updates with rollback on failure.

---

## Medium-term (v2.0)

### Multi-Workflow Support
- Extend the frontend to manage multiple workflow types beyond ETF orders.
- Workflow selector in the header.
- Auto-generate trigger forms from Mermaid payload definitions (generalizes the v1.x inline forms to any workflow).

### Positions as Live Data
- Connect the positions panel to a real portfolio system or database.
- P&L calculations from order history and market data.
- Aggregate positions from completed orders.

### Notifications
- Toast/bell notifications when orders change state (especially external changes).
- Email/Slack integration for critical state changes (REJECTED, CANCELLED).

### Batch Operations
- Multi-select orders in the blotter for bulk actions (Cancel All, Accept All).
- CSV/Excel export of order blotter and positions.

### Dashboard Analytics
- Order volume over time.
- Average time-to-completion per workflow state.
- Rejection/cancellation rates.

### Micro Front-End (MFE) Architecture
- Decompose the monolith into independently deployable MFEs: Order Entry, Blotter, Market Color, Positions, Order Detail.
- Each panel already has isolated state (React Query hooks) — extract into standalone packages with a shared shell.
- Use Module Federation (Webpack 5) or import maps for runtime composition.
- Enables independent team ownership, deploy cycles, and tech stack evolution per panel.
- Shared design tokens and event bus for cross-MFE communication (order selection, ticker context).

---

## Long-term (v3.0)

### Workflow Designer
- Visual drag-and-drop Mermaid editor integrated into the frontend.
- Live preview of state machine diagrams.
- Version management UI for workflow definitions.

### Multi-Database Support
- PostgreSQL for production deployments.
- Connection pooling with async SQLAlchemy.
- Database migrations with Alembic.

### Task Queue
- Offload long-running actions to Celery or Prefect workers.
- Background basket delivery, share issuance simulations.
- Status tracking with progress indicators in the UI.

### Compliance & Reporting
- Regulatory reporting exports (FIX protocol format).
- Immutable audit log with cryptographic chaining.
- Data retention policies and archival.

### Multi-Tenancy
- Isolated workflow namespaces per desk/team.
- Tenant-specific branding and configuration.

### Mobile / Responsive
- Responsive layout for tablet access on the trading floor.
- Progressive Web App (PWA) for offline order viewing.
