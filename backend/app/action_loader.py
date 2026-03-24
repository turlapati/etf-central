"""
Action Loader: Automatically discovers and registers all actions.

This module imports all action modules to trigger decorator registration,
then syncs the action registry to the database.
"""
import logging
from sqlmodel import Session

logger = logging.getLogger(__name__)


def load_all_actions():
    """
    Import all action modules to trigger @action decorator registration.
    
    This must be called before the action registry is used.
    """
    logger.info("Loading action library...")
    
    # Import all action modules - decorators will execute and populate registry
    # These imports are intentionally "unused" - they trigger @action decorators
    from app.actions import communication  # noqa: F401
    from app.actions import payment  # noqa: F401
    from app.actions import validation  # noqa: F401
    from app.actions import workflow_control  # noqa: F401
    
    from app.registry import ACTION_REGISTRY
    
    action_count = len(ACTION_REGISTRY)
    logger.info(f"Loaded {action_count} actions into registry")
    
    # Log actions by category
    from app.registry import get_categories, list_actions
    for category in get_categories():
        actions = list_actions(category=category)
        action_names = [a.name for a in actions]
        logger.info(f"  {category}: {', '.join(action_names)}")
    
    return action_count


def sync_actions_to_database(session: Session):
    """
    Synchronize the in-memory action registry to the database.
    
    This should be called on application startup after load_all_actions().
    """
    logger.info("Syncing actions to database...")
    
    from app.registry import sync_actions_to_db
    
    try:
        sync_actions_to_db(session)
        logger.info("Action sync completed successfully")
    except Exception as e:
        logger.error(f"Failed to sync actions to database: {str(e)}")
        raise


def initialize_action_system(session: Session):
    """
    Complete initialization: load actions and sync to database.
    
    Call this once on application startup.
    """
    logger.info("Initializing action system...")
    
    action_count = load_all_actions()
    sync_actions_to_database(session)
    
    logger.info(f"Action system initialized with {action_count} actions")
    return action_count
