"""PortfolioRunner: equal-weight allocation across multiple stocks.

Each stock gets initial_capital / N and manages its allocation independently.
Freed capital from selling stays within its own allocation (no cross-stock sharing).
Combined portfolio equity is tracked alongside per-stock equity.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.backtest_runner import BacktestRunner, DEFAULT_RISK_PARAMS
from app.engine.base_strategy import SignalType
from app.engine.position_manager import PositionManager
from app.engine.risk_controller import RiskController
from app.models.backtest import Backtest, BacktestDailyReturn, BacktestTrade

logger = logging.getLogger(__name__)


class PortfolioRunner:
    COMMISSION_RATE = 0.001425
    TAX_RATE = 0.003
    LOT_SIZE = 1000

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
            raise ValueError("Portfolio mode requires a non-empty stock_ids list")

        try:
            backtest.status = "running"
            await self.db.commit()

            # 2. Load strategy
            helper = BacktestRunner(self.db)
            strategy = await helper._load_strategy(backtest.strategy_id)

            # Parse risk parameters
            risk_params = {**DEFAULT_RISK_PARAMS, **(backtest.risk_params or {})}

            # 3. Calculate per-stock capital
            per_stock_capital = backtest.initial_capital / len(stock_ids)

            # 4. Load market data for all stocks
            market_data_map = {}
            for sid in stock_ids:
                market_data_map[sid] = await helper._load_market_data(
                    sid, backtest.start_date, backtest.end_date
                )

            # 5. Create PositionManager and RiskController per stock
            positions: dict[str, PositionManager] = {}
            risk_controllers: dict[str, RiskController] = {}

            for sid in stock_ids:
                positions[sid] = PositionManager(
                    initial_capital=per_stock_capital,
                    position_size_pct=risk_params["position_size_pct"],
                    max_scale_in=risk_params["max_scale_in_times"],
                    commission_rate=self.COMMISSION_RATE,
                    tax_rate=self.TAX_RATE,
                    lot_size=self.LOT_SIZE,
                )
                risk_controllers[sid] = RiskController(
                    stop_loss_pct=risk_params["stop_loss_pct"],
                    take_profit_pct=risk_params["take_profit_pct"],
                    trailing_stop_pct=risk_params["trailing_stop_pct"],
                )

            allow_scale_in = risk_params["allow_scale_in"]
            max_scale_in = risk_params["max_scale_in_times"]

            # 6. Build union of all trading dates
            all_dates: set = set()
            price_lookup: dict[str, dict] = {}  # {stock_id: {date: close_price}}

            for sid in stock_ids:
                price_lookup[sid] = {}
                for p in market_data_map[sid].prices:
                    d = p["date"]
                    if backtest.start_date <= d <= backtest.end_date:
                        all_dates.add(d)
                        price_lookup[sid][d] = p["close_price"]

            trading_dates = sorted(all_dates)
            if not trading_dates:
                backtest.status = "completed"
                backtest.result = {}
                backtest.completed_at = datetime.utcnow()
                await self.db.commit()
                return {}

            # 7. Day loop
            trades: list[BacktestTrade] = []
            daily_returns: list[BacktestDailyReturn] = []
            prev_portfolio_equity = backtest.initial_capital
            prev_stock_equity: dict[str, float] = {
                sid: per_stock_capital for sid in stock_ids
            }

            for current_date in trading_dates:
                for sid in stock_ids:
                    close_price = price_lookup[sid].get(current_date)
                    if close_price is None:
                        continue  # stock has no data for this date

                    pm = positions[sid]
                    rc = risk_controllers[sid]

                    # Update tracking for trailing stop
                    pm.update_high(close_price)

                    # Risk check (overrides strategy)
                    risk_signal = rc.check(close_price, pm)

                    if risk_signal and pm.holding_quantity > 0:
                        trade_dict = pm.sell(close_price, current_date)
                        if trade_dict:
                            trades.append(BacktestTrade(
                                backtest_id=backtest_id,
                                trade_date=trade_dict["date"],
                                stock_id=sid,
                                direction=trade_dict["direction"],
                                price=trade_dict["price"],
                                quantity=trade_dict["quantity"],
                                commission=trade_dict["commission"],
                                tax=trade_dict["tax"],
                                realized_pnl=trade_dict["realized_pnl"],
                                reason=risk_signal.reason,
                            ))
                    else:
                        # Strategy signal
                        signal = strategy.on_data(
                            current_date, market_data_map[sid]
                        )

                        if signal.signal_type == SignalType.BUY:
                            can_buy = False
                            if pm.holding_quantity == 0:
                                can_buy = True
                            elif allow_scale_in and pm.scale_in_count < max_scale_in:
                                can_buy = True

                            if can_buy:
                                trade_dict = pm.buy(close_price, current_date)
                                if trade_dict:
                                    trades.append(BacktestTrade(
                                        backtest_id=backtest_id,
                                        trade_date=trade_dict["date"],
                                        stock_id=sid,
                                        direction=trade_dict["direction"],
                                        price=trade_dict["price"],
                                        quantity=trade_dict["quantity"],
                                        commission=trade_dict["commission"],
                                        tax=trade_dict["tax"],
                                        realized_pnl=trade_dict["realized_pnl"],
                                        reason="strategy",
                                    ))

                        elif signal.signal_type == SignalType.SELL and pm.holding_quantity > 0:
                            trade_dict = pm.sell(close_price, current_date)
                            if trade_dict:
                                trades.append(BacktestTrade(
                                    backtest_id=backtest_id,
                                    trade_date=trade_dict["date"],
                                    stock_id=sid,
                                    direction=trade_dict["direction"],
                                    price=trade_dict["price"],
                                    quantity=trade_dict["quantity"],
                                    commission=trade_dict["commission"],
                                    tax=trade_dict["tax"],
                                    realized_pnl=trade_dict["realized_pnl"],
                                    reason="strategy",
                                ))

                # Record per-stock daily returns
                for sid in stock_ids:
                    close_price = price_lookup[sid].get(current_date)
                    if close_price is None:
                        continue

                    pm = positions[sid]
                    equity = pm.get_total_equity(close_price)
                    position_value = equity - pm.available_capital
                    prev_eq = prev_stock_equity[sid]
                    daily_ret = (
                        (equity - prev_eq) / prev_eq if prev_eq > 0 else None
                    )

                    daily_returns.append(BacktestDailyReturn(
                        backtest_id=backtest_id,
                        date=current_date,
                        stock_id=sid,
                        position_value=position_value,
                        cash=pm.available_capital,
                        total_equity=equity,
                        daily_return=daily_ret,
                    ))
                    prev_stock_equity[sid] = equity

                # Record combined portfolio daily return (stock_id=None)
                portfolio_equity = sum(
                    pm.get_total_equity(
                        price_lookup[sid].get(current_date, 0.0)
                    )
                    for sid, pm in positions.items()
                )
                portfolio_position_value = portfolio_equity - sum(
                    pm.available_capital for pm in positions.values()
                )
                portfolio_cash = sum(
                    pm.available_capital for pm in positions.values()
                )
                portfolio_daily_ret = (
                    (portfolio_equity - prev_portfolio_equity) / prev_portfolio_equity
                    if prev_portfolio_equity > 0
                    else None
                )

                daily_returns.append(BacktestDailyReturn(
                    backtest_id=backtest_id,
                    date=current_date,
                    stock_id=None,
                    position_value=portfolio_position_value,
                    cash=portfolio_cash,
                    total_equity=portfolio_equity,
                    daily_return=portfolio_daily_ret,
                ))
                prev_portfolio_equity = portfolio_equity

            # 8. Save trades and daily returns
            for trade in trades:
                self.db.add(trade)
            for dr in daily_returns:
                self.db.add(dr)

            # 9. Calculate metrics
            # Portfolio-level metrics from combined daily returns
            portfolio_daily = [
                dr for dr in daily_returns if dr.stock_id is None
            ]
            portfolio_trades = trades  # all trades belong to this portfolio
            portfolio_metrics = BacktestRunner._calculate_metrics(
                portfolio_daily, portfolio_trades, backtest.initial_capital
            )

            # Per-stock metrics
            per_stock_results: dict[str, dict] = {}
            for sid in stock_ids:
                stock_daily = [
                    dr for dr in daily_returns if dr.stock_id == sid
                ]
                stock_trades = [t for t in trades if t.stock_id == sid]
                per_stock_results[sid] = BacktestRunner._calculate_metrics(
                    stock_daily, stock_trades, per_stock_capital
                )

            # 10. Update backtest record
            backtest.status = "completed"
            backtest.result = {
                "portfolio_metrics": portfolio_metrics,
                "per_stock_results": per_stock_results,
                "per_stock_capital": round(per_stock_capital, 2),
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
