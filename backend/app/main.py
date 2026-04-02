import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, update

from app.api.alerts import router as alerts_router
from app.api.email_reports import router as email_reports_router
from app.api.backtests import router as backtests_router
from app.api.notifications import router as notifications_router
from app.api.stocks import router as stocks_router
from app.api.watchlist import router as watchlist_router
from app.auth.router import router as auth_router
from app.config import settings
from app.database import AsyncSessionLocal
from app.logging_config import setup_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.models.backtest import Backtest

setup_logging()
logger = logging.getLogger(__name__)

# --- Sentry error monitoring ---
if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 將卡住的回測標記為 failed
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(Backtest)
            .where(Backtest.status.in_(["pending", "running"]))
            .values(
                status="failed",
                error_message="伺服器重啟，回測中斷。請重新執行。",
            )
        )
        if result.rowcount > 0:
            logger.info("已將 %d 筆卡住的回測標記為 failed", result.rowcount)
        await session.commit()
    yield


app = FastAPI(title="Stock Tracer API", version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(stocks_router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(backtests_router, prefix="/api/v1/backtests", tags=["backtests"])
app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(watchlist_router, prefix="/api/v1/watchlist", tags=["watchlist"])
app.include_router(
    notifications_router, prefix="/api/v1/notifications", tags=["notifications"]
)
app.include_router(
    email_reports_router, prefix="/api/v1/email-reports", tags=["email-reports"]
)


@app.get("/health")
async def health():
    result = {"status": "ok", "db": "ok", "redis": "ok"}

    # Check DB connection
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Health check: DB connection failed", exc_info=True)
        result["db"] = "error"

    # Check Redis connection
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await r.ping()
        finally:
            await r.aclose()
    except Exception:
        logger.warning("Health check: Redis connection failed", exc_info=True)
        result["redis"] = "error"

    if result["db"] != "ok" or result["redis"] != "ok":
        result["status"] = "degraded"

    return result
