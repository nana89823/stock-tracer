import os
from pathlib import Path

from pydantic_settings import BaseSettings

# .env is at project root (two levels up from this file)
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Default secret key for LOCAL DEVELOPMENT ONLY.
# In production, you MUST set the SECRET_KEY environment variable.
_DEV_SECRET_KEY = "dev-secret-key-NOT-FOR-PRODUCTION"


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://stock_tracer:stock_tracer_dev@localhost:5432/stock_tracer"
    )
    database_url_sync: str = (
        "postgresql://stock_tracer:stock_tracer_dev@localhost:5432/stock_tracer"
    )
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = _DEV_SECRET_KEY
    cors_origins: list[str] = ["http://localhost:3000"]
    sentry_dsn: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Stock Tracer"
    email_report_enabled: bool = False

    class Config:
        env_file = str(_ENV_FILE)
        extra = "ignore"


settings = Settings()

# Guard: refuse to start in production without a real secret key
if (
    os.getenv("ENV", "development").lower() in ("production", "prod")
    and settings.secret_key == _DEV_SECRET_KEY
):
    raise RuntimeError(
        "SECRET_KEY environment variable must be set to a secure value in production. "
        "Do not use the default development key."
    )
