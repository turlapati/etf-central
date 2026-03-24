from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.database import create_db_and_tables, initialize_action_system, engine
from app.api import state_machines_api, instances
from app.config import settings
from app.trigger_router import get_trigger_router, reload_trigger_routes

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlmodel import Session, select

    logger.info("Starting ETF Central backend...")

    create_db_and_tables()
    logger.info("Database tables created")

    initialize_action_system()
    logger.info("Action library initialized")

    # Auto-seed the etf_order workflow if it doesn't exist
    with Session(engine) as session:
        from app.models import StateMachineDefinition
        existing = session.exec(
            select(StateMachineDefinition).where(StateMachineDefinition.name == "etf_order")
        ).first()

        if not existing:
            logger.info("Seeding etf_order workflow definition...")
            from app.seed import seed_etf_workflow
            seed_etf_workflow(session)
            logger.info("etf_order workflow seeded successfully")

    with Session(engine) as session:
        trigger_router = get_trigger_router(session)
        app.include_router(trigger_router)
        logger.info("Dynamic trigger routes registered")

    logger.info("Backend ready — http://localhost:8000/docs")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="ETF Central — Backend API",
    description="Workflow engine powering ETF creation/redemption order lifecycle",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
_cors_origins = (
    ["*"]
    if settings.cors_origins.strip() == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)
_cors_headers = [h.strip() for h in settings.cors_allow_headers.split(",") if h.strip()]

from app.middleware import CorrelationIdMiddleware

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=_cors_headers,
    expose_headers=["X-Correlation-Id"],
)

# REST API routers only
app.include_router(state_machines_api.router)
app.include_router(instances.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "etf-central"}


@app.post("/admin/reload-routes")
def admin_reload_routes():
    """Reload dynamic trigger routes after workflow definition changes."""
    from sqlmodel import Session

    with Session(engine) as session:
        trigger_router = reload_trigger_routes(session)
        app.include_router(trigger_router)

    app.openapi_schema = None
    logger.info("Trigger routes reloaded")
    return {
        "status": "success",
        "message": "Routes reloaded. Paths are stable across workflow versions.",
    }
