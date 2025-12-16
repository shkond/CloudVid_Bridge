"""Heroku Scheduler task to check queue and scale worker dyno.

This script is designed to be run by Heroku Scheduler every 10 minutes.
It checks if there are pending or active jobs in the queue:
- If jobs exist: ensure worker dyno is running
- If queue is empty: stop worker dyno to save resources

Usage:
    python -m app.tasks.check_and_scale_worker

Configuration:
    Requires HEROKU_API_KEY and HEROKU_APP_NAME environment variables.
"""

import asyncio
import logging
import sys

from app.config import get_settings
from app.core.heroku_client import HerokuClient
from app.database import close_db, get_db_context, init_db
from app.queue.repositories import QueueRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def check_queue_has_jobs() -> bool:
    """Check if there are pending or active jobs in the queue.
    
    Returns:
        True if there are jobs to process
    """
    async with get_db_context() as db:
        repo = QueueRepository(db)

        # Check for pending jobs
        pending_jobs = await repo.get_pending_jobs()
        if pending_jobs:
            logger.info("Found %d pending jobs", len(pending_jobs))
            return True

        # Check for active jobs (downloading/uploading)
        active_jobs = await repo.get_active_jobs()
        if active_jobs:
            logger.info("Found %d active jobs", len(active_jobs))
            return True

        logger.info("No pending or active jobs found")
        return False


async def check_and_scale_worker() -> None:
    """Main entry point: check queue and scale worker accordingly."""
    logger.info("=" * 60)
    logger.info("Starting worker scaling check...")
    logger.info("=" * 60)

    settings = get_settings()

    # Validate Heroku configuration
    if not settings.heroku_api_key or not settings.heroku_app_name:
        logger.error(
            "HEROKU_API_KEY and HEROKU_APP_NAME environment variables required"
        )
        sys.exit(1)

    await init_db()

    try:
        # Check if there are jobs to process
        has_jobs = await check_queue_has_jobs()

        # Create Heroku client
        heroku = HerokuClient(
            api_key=settings.heroku_api_key,
            app_name=settings.heroku_app_name,
        )

        if has_jobs:
            # Ensure worker is running
            logger.info("Jobs found - ensuring worker is running...")
            await heroku.ensure_worker_running()
            logger.info("Worker dyno is running")
        else:
            # Stop worker to save resources
            logger.info("No jobs - stopping worker to save dyno hours...")
            await heroku.stop_worker()
            logger.info("Worker dyno stopped")

    except Exception:
        logger.exception("Failed to check/scale worker")
        sys.exit(1)

    finally:
        await close_db()
        logger.info("=" * 60)
        logger.info("Worker scaling check complete")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_and_scale_worker())
