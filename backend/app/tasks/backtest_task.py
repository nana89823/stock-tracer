import asyncio
import logging

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery
from app.config import settings
from app.engine.backtest_runner import BacktestRunner
from app.engine.batch_runner import BatchRunner
from app.engine.portfolio_runner import PortfolioRunner
from app.database import AsyncSessionLocal
from app.models.backtest import Backtest

logger = logging.getLogger(__name__)

# Sync engine/session for Celery worker (separate process, cannot use async)
_sync_engine = create_engine(settings.database_url_sync)
SyncSessionLocal = sessionmaker(_sync_engine, expire_on_commit=False)


async def _run_backtest_async(backtest_id: int) -> None:
    """Run backtest using the appropriate runner based on mode."""
    async with AsyncSessionLocal() as session:
        # Load backtest to determine mode
        result = await session.execute(
            select(Backtest).where(Backtest.id == backtest_id)
        )
        backtest = result.scalar_one()
        mode = backtest.mode or "single"

        if mode == "batch":
            runner = BatchRunner(session)
        elif mode == "portfolio":
            runner = PortfolioRunner(session)
        else:
            runner = BacktestRunner(session)

        await runner.run(backtest_id)


@celery.task(name="run_backtest", bind=True, max_retries=0)
def run_backtest_task(self, backtest_id: int) -> dict:
    """Celery task to execute a backtest."""
    logger.info("Starting backtest %d (celery task %s)", backtest_id, self.request.id)

    try:
        # BacktestRunner is async, so we use asyncio.run() to execute it
        asyncio.run(_run_backtest_async(backtest_id))
        return {"status": "completed", "backtest_id": backtest_id}

    except SoftTimeLimitExceeded:
        logger.error("Backtest %d timed out", backtest_id)
        # Mark as failed in DB using sync session
        with SyncSessionLocal() as session:
            backtest = session.get(Backtest, backtest_id)
            if backtest:
                backtest.status = "failed"
                backtest.error_message = "回測執行超時"
                session.commit()
        return {"status": "failed", "backtest_id": backtest_id, "error": "回測執行超時"}

    except Exception as exc:
        logger.exception("Backtest %d failed", backtest_id)
        # BacktestRunner.run() already marks the backtest as failed in its
        # own except block, so we only need to handle edge cases where the
        # runner itself could not update the DB.
        return {"status": "failed", "backtest_id": backtest_id, "error": str(exc)}
