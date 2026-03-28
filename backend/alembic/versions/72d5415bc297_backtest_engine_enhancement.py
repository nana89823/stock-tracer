"""backtest engine enhancement

Revision ID: 72d5415bc297
Revises: a037098928b5
Create Date: 2026-03-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "72d5415bc297"
down_revision = "a037098928b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backtest table: add mode, stock_ids, risk_params; make stock_id nullable
    op.add_column("backtests", sa.Column("mode", sa.String(10), server_default="single", nullable=False))
    op.add_column("backtests", sa.Column("stock_ids", postgresql.JSONB(), nullable=True))
    op.add_column("backtests", sa.Column("risk_params", postgresql.JSONB(), nullable=True))
    op.alter_column("backtests", "stock_id", existing_type=sa.String(10), nullable=True)

    # BacktestTrade table: add reason
    op.add_column("backtest_trades", sa.Column("reason", sa.String(20), server_default="strategy", nullable=False))

    # BacktestDailyReturn table: add stock_id for per-stock tracking
    op.add_column("backtest_daily_returns", sa.Column("stock_id", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("backtest_daily_returns", "stock_id")
    op.drop_column("backtest_trades", "reason")
    op.drop_column("backtests", "risk_params")
    op.drop_column("backtests", "stock_ids")
    op.drop_column("backtests", "mode")
    op.alter_column("backtests", "stock_id", existing_type=sa.String(10), nullable=False)
