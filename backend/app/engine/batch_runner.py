"""BatchRunner: runs a strategy independently on multiple stocks.

Each stock gets its own capital pool equal to backtest.initial_capital.
Results are aggregated into per-stock metrics and a summary.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.backtest_runner import BacktestRunner
from app.models.backtest import Backtest

logger = logging.getLogger(__name__)


class BatchRunner:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def run(self, backtest_id: int) -> dict:
        # 1. Load backtest from DB
        result = await self.db.execute(
            select(Backtest).where(Backtest.id == backtest_id)
        )
        backtest = result.scalar_one_or_none()
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")

        stock_ids = backtest.stock_ids
        if not stock_ids or not isinstance(stock_ids, list) or len(stock_ids) == 0:
            raise ValueError("Batch mode requires a non-empty stock_ids list")

        try:
            backtest.status = "running"
            await self.db.commit()

            # 2. Load strategy once (shared across all stocks)
            single_runner = BacktestRunner(self.db)
            strategy = await single_runner._load_strategy(backtest.strategy_id)

            # 3. Run each stock independently with its own capital pool
            per_stock_results: dict[str, dict] = {}
            all_trades = []
            all_daily_returns = []

            for stock_id in stock_ids:
                logger.info(
                    "Batch backtest %d: running stock %s", backtest_id, stock_id
                )
                runner = BacktestRunner(self.db)
                run_result = await runner.run_single(stock_id, backtest, strategy)

                per_stock_results[stock_id] = run_result["metrics"]
                all_trades.extend(run_result["trades"])
                all_daily_returns.extend(run_result["daily_returns"])

            # 4. Save all trades and daily returns to DB
            for trade in all_trades:
                self.db.add(trade)
            for dr in all_daily_returns:
                self.db.add(dr)

            # 5. Calculate summary metrics
            summary = self._calculate_summary(per_stock_results, stock_ids)

            # 6. Save result and mark completed
            backtest.status = "completed"
            backtest.result = {
                "per_stock_results": per_stock_results,
                "summary": summary,
            }
            backtest.completed_at = datetime.utcnow()
            await self.db.commit()

            return backtest.result

        except Exception as e:
            backtest.status = "failed"
            backtest.error_message = str(e)
            backtest.completed_at = datetime.utcnow()
            await self.db.commit()
            raise

    @staticmethod
    def _calculate_summary(
        per_stock_results: dict[str, dict], stock_ids: list[str]
    ) -> dict:
        """Aggregate per-stock metrics into a batch summary."""
        returns = {}
        win_rates = []
        total_trades_sum = 0

        for sid in stock_ids:
            metrics = per_stock_results.get(sid, {})
            tr = metrics.get("total_return", 0.0)
            returns[sid] = tr
            if "win_rate" in metrics:
                win_rates.append(metrics["win_rate"])
            total_trades_sum += metrics.get("total_trades", 0)

        valid_returns = [v for v in returns.values() if v is not None]

        avg_return = (
            sum(valid_returns) / len(valid_returns) if valid_returns else 0.0
        )

        best_stock = max(returns, key=returns.get) if returns else None
        worst_stock = min(returns, key=returns.get) if returns else None

        overall_win_rate = (
            sum(win_rates) / len(win_rates) if win_rates else 0.0
        )

        return {
            "avg_return": round(avg_return, 6),
            "best_stock": best_stock,
            "best_stock_return": round(returns.get(best_stock, 0.0), 6) if best_stock else 0.0,
            "worst_stock": worst_stock,
            "worst_stock_return": round(returns.get(worst_stock, 0.0), 6) if worst_stock else 0.0,
            "overall_win_rate": round(overall_win_rate, 4),
            "total_trades": total_trades_sum,
            "num_stocks": len(stock_ids),
        }
