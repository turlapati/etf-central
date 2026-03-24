from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event
from sqlalchemy.engine import Engine
from pathlib import Path
from app.config import settings


# Create data directory if it doesn't exist
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Create SQLite engine with optimizations
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False}
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite PRAGMAs for optimal performance and concurrency."""
    cursor = dbapi_conn.cursor()
    cursor.execute(f"PRAGMA journal_mode={settings.sqlite_pragma_journal_mode}")
    cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_pragma_busy_timeout}")
    cursor.execute(f"PRAGMA synchronous={settings.sqlite_pragma_synchronous}")
    cursor.execute(f"PRAGMA cache_size={settings.sqlite_pragma_cache_size}")
    cursor.execute(f"PRAGMA temp_store={settings.sqlite_pragma_temp_store}")
    cursor.close()


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def initialize_action_system():
    """Initialize action library system on startup."""
    import logging
    from app.action_loader import initialize_action_system as init_actions
    
    logger = logging.getLogger(__name__)
    logger.info("Initializing action system...")
    
    with Session(engine) as session:
        try:
            action_count = init_actions(session)
            logger.info(f"Action system initialized with {action_count} actions")
        except Exception as e:
            logger.error(f"Failed to initialize action system: {str(e)}")
            raise


def get_session():
    """Dependency for FastAPI to get database session."""
    with Session(engine) as session:
        yield session


def get_engine():
    """Get the database engine for direct use."""
    return engine
