import math
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.base_strategy import BaseStrategy, MarketData, SignalType
from app.engine.position_manager import PositionManager
from app.engine.risk_controller import RiskController
from app.engine.strategies import BUILTIN_STRATEGIES
from app.models.backtest import Backtest, BacktestDailyReturn, BacktestTrade
from app.models.major_holders import MajorHolders
from app.models.margin_trading import MarginTrading
from app.models.raw_chip import RawChip
from app.models.raw_price import RawPrice
from app.models.strategy import Strategy

DEFAULT_RISK_PARAMS = {
    "stop_loss_pct": None,
    "take_profit_pct": None,
    "trailing_stop_pct": None,
    "position_size_pct": 100.0,
    "allow_scale_in": False,
    "max_scale_in_times": 0,
}


class BacktestRunner:
    COMMISSION_RATE = 0.001425
    TAX_RATE = 0.003  # sell only
    LOT_SIZE = 1000

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def run(self, backtest_id: int) -> dict:
        # 1. Load backtest config from DB
        result = await self.db.execute(
            select(Backtest).where(Backtest.id == backtest_id)
        )
        backtest = result.scalar_one_or_none()
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")

        try:
            backtest.status = "running"
            await self.db.commit()

            # 2. Load strategy
            strategy = await self._load_strategy(backtest.strategy_id)

            # 3. Run single stock simulation
            run_result = await self.run_single(backtest.stock_id, backtest, strategy)

            # 4. Save trades and daily returns
            for trade in run_result["trades"]:
                self.db.add(trade)
            for dr in run_result["daily_returns"]:
                self.db.add(dr)

            # 5. Update backtest record
            backtest.status = "completed"
            backtest.result = run_result["metrics"]
            backtest.completed_at = datetime.utcnow()
            await self.db.commit()

            return run_result["metrics"]

        except Exception as e:
            backtest.status = "failed"
            backtest.error_message = str(e)
            backtest.completed_at = datetime.utcnow()
            await self.db.commit()
            raise

    async def run_single(
        self, stock_id: str, backtest: Backtest, strategy: BaseStrategy | None = None
    ) -> dict:
        """Run backtest for a single stock.

        Loads market data, runs simulation, returns trades/daily_returns/metrics.
        Designed for reuse by BatchRunner and PortfolioRunner.

        Args:
            stock_id: Stock to simulate.
            backtest: Backtest record (provides dates, capital, risk_params, id).
            strategy: Pre-loaded strategy. If None, loads from backtest.strategy_id.

        Returns:
            Dict with keys: trades, daily_returns, metrics.
        """
        if strategy is None:
            strategy = await self._load_strategy(backtest.strategy_id)

        market_data = await self._load_market_data(
            stock_id, backtest.start_date, backtest.end_date
        )

        run_result = self._simulate(
            strategy=strategy,
            stock_id=stock_id,
            market_data=market_data,
            initial_capital=backtest.initial_capital,
            backtest_id=backtest.id,
            backtest=backtest,
        )

        return run_result

    async def _load_strategy(self, strategy_id: int) -> BaseStrategy:
        result = await self.db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy_record = result.scalar_one_or_none()
        if not strategy_record:
            raise ValueError(f"Strategy {strategy_id} not found")

        strategy_type = strategy_record.strategy_type
        if strategy_type not in BUILTIN_STRATEGIES:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

        cls = BUILTIN_STRATEGIES[strategy_type]["cls"]
        params = strategy_record.params or BUILTIN_STRATEGIES[strategy_type]["default_params"]
        return cls(params=params)

    async def _load_market_data(
        self, stock_id: str, start_date: date, end_date: date
    ) -> MarketData:
        # Load prices
        result = await self.db.execute(
            select(RawPrice)
            .where(RawPrice.stock_id == stock_id, RawPrice.date <= end_date)
            .order_by(RawPrice.date)
        )
        prices = [
            {
                "date": r.date,
                "stock_id": r.stock_id,
                "open_price": r.open_price,
                "high_price": r.high_price,
                "low_price": r.low_price,
                "close_price": r.close_price,
                "trade_volume": r.trade_volume,
            }
            for r in result.scalars().all()
        ]

        # Load chips
        result = await self.db.execute(
            select(RawChip)
            .where(RawChip.stock_id == stock_id, RawChip.date <= end_date)
            .order_by(RawChip.date)
        )
        chips = [
            {
                "date": r.date,
                "stock_id": r.stock_id,
                "foreign_net": r.foreign_net,
                "trust_net": r.trust_net,
                "dealer_net": r.dealer_net,
                "total_net": r.total_net,
            }
            for r in result.scalars().all()
        ]

        # Load holders
        result = await self.db.execute(
            select(MajorHolders)
            .where(MajorHolders.stock_id == stock_id, MajorHolders.date <= end_date)
            .order_by(MajorHolders.date, MajorHolders.holding_level)
        )
        holders = [
            {
                "date": r.date,
                "stock_id": r.stock_id,
                "holding_level": r.holding_level,
                "holder_count": r.holder_count,
                "share_count": r.share_count,
                "holding_ratio": r.holding_ratio,
            }
            for r in result.scalars().all()
        ]

        # Load margin
        result = await self.db.execute(
            select(MarginTrading)
            .where(MarginTrading.stock_id == stock_id, MarginTrading.date <= end_date)
            .order_by(MarginTrading.date)
        )
        margin = [
            {
                "date": r.date,
                "stock_id": r.stock_id,
                "margin_balance": r.margin_balance,
                "margin_limit": r.margin_limit,
                "short_balance": r.short_balance,
                "short_limit": r.short_limit,
            }
            for r in result.scalars().all()
        ]

        return MarketData(prices=prices, chips=chips, holders=holders, margin=margin)

    def _parse_risk_params(self, backtest: Backtest) -> dict:
        """Merge backtest.risk_params with defaults for backward compatibility."""
        params = backtest.risk_params or {}
        return {**DEFAULT_RISK_PARAMS, **params}

    def _simulate(
        self,
        strategy: BaseStrategy,
        stock_id: str,
        market_data: MarketData,
        initial_capital: float,
        backtest_id: int,
        backtest: Backtest,
    ) -> dict:
        # Parse risk parameters (defaults when None -> backward compatible)
        risk_params = self._parse_risk_params(backtest)

        # Create PositionManager
        position_manager = PositionManager(
            initial_capital=initial_capital,
            position_size_pct=risk_params["position_size_pct"],
            max_scale_in=risk_params["max_scale_in_times"],
            commission_rate=self.COMMISSION_RATE,
            tax_rate=self.TAX_RATE,
            lot_size=self.LOT_SIZE,
        )

        # Create RiskController
        risk_controller = RiskController(
            stop_loss_pct=risk_params["stop_loss_pct"],
            take_profit_pct=risk_params["take_profit_pct"],
            trailing_stop_pct=risk_params["trailing_stop_pct"],
        )

        allow_scale_in = risk_params["allow_scale_in"]
        max_scale_in = risk_params["max_scale_in_times"]

        trades: list[BacktestTrade] = []
        daily_returns: list[BacktestDailyReturn] = []
        prev_equity = initial_capital

        # Get trading dates within simulation range
        trading_dates = sorted(set(
            p["date"] for p in market_data.prices
            if p["date"] >= market_data.prices[0]["date"]
        ))

        if not trading_dates:
            return {"trades": [], "daily_returns": [], "metrics": {}}

        for current_date in trading_dates:
            # Get current close price
            close_price = None
            for p in market_data.prices:
                if p["date"] == current_date and p["stock_id"] == stock_id:
                    close_price = p["close_price"]
                    break

            if close_price is None:
                continue

            # 1. Update position tracking (for trailing stop)
            position_manager.update_high(close_price)

            # 2. Risk check (overrides strategy)
            risk_signal = risk_controller.check(close_price, position_manager)

            if risk_signal and position_manager.holding_quantity > 0:
                # Risk-triggered sell: sell all holdings
                trade_dict = position_manager.sell(close_price, current_date)
                if trade_dict:
                    trades.append(BacktestTrade(
                        backtest_id=backtest_id,
                        trade_date=trade_dict["date"],
                        stock_id=stock_id,
                        direction=trade_dict["direction"],
                        price=trade_dict["price"],
                        quantity=trade_dict["quantity"],
                        commission=trade_dict["commission"],
                        tax=trade_dict["tax"],
                        realized_pnl=trade_dict["realized_pnl"],
                        reason=risk_signal.reason,
                    ))
            else:
                # 3. Strategy signal
                signal = strategy.on_data(current_date, market_data)

                if signal.signal_type == SignalType.BUY:
                    # Check if we can buy: either no holdings or scale-in allowed
                    can_buy = False
                    if position_manager.holding_quantity == 0:
                        can_buy = True
                    elif allow_scale_in and position_manager.scale_in_count < max_scale_in:
                        can_buy = True

                    if can_buy:
                        # Let PositionManager auto-size based on position_size_pct
                        trade_dict = position_manager.buy(
                            close_price, current_date,
                        )
                        if trade_dict:
                            trades.append(BacktestTrade(
                                backtest_id=backtest_id,
                                trade_date=trade_dict["date"],
                                stock_id=stock_id,
                                direction=trade_dict["direction"],
                                price=trade_dict["price"],
                                quantity=trade_dict["quantity"],
                                commission=trade_dict["commission"],
                                tax=trade_dict["tax"],
                                realized_pnl=trade_dict["realized_pnl"],
                                reason="strategy",
                            ))

                elif signal.signal_type == SignalType.SELL and position_manager.holding_quantity > 0:
                    # Sell all holdings on strategy sell signal
                    trade_dict = position_manager.sell(
                        close_price, current_date,
                    )
                    if trade_dict:
                        trades.append(BacktestTrade(
                            backtest_id=backtest_id,
                            trade_date=trade_dict["date"],
                            stock_id=stock_id,
                            direction=trade_dict["direction"],
                            price=trade_dict["price"],
                            quantity=trade_dict["quantity"],
                            commission=trade_dict["commission"],
                            tax=trade_dict["tax"],
                            realized_pnl=trade_dict["realized_pnl"],
                            reason="strategy",
                        ))

            # 4. Record daily equity
            total_equity = position_manager.get_total_equity(close_price)
            position_value = total_equity - position_manager.available_capital
            daily_ret = (
                (total_equity - prev_equity) / prev_equity
                if prev_equity > 0 else None
            )

            daily_returns.append(BacktestDailyReturn(
                backtest_id=backtest_id,
                date=current_date,
                stock_id=stock_id,
                position_value=position_value,
                cash=position_manager.available_capital,
                total_equity=total_equity,
                daily_return=daily_ret,
            ))

            prev_equity = total_equity

        # Calculate metrics
        metrics = self._calculate_metrics(daily_returns, trades, initial_capital)

        return {"trades": trades, "daily_returns": daily_returns, "metrics": metrics}

    @staticmethod
    def _get_close(prices: list[dict], stock_id: str, target_date: date) -> float:
        for p in reversed(prices):
            if p["stock_id"] == stock_id and p["date"] <= target_date:
                return p["close_price"]
        return 0.0

    @staticmethod
    def _calculate_metrics(
        daily_returns: list[BacktestDailyReturn],
        trades: list[BacktestTrade],
        initial_capital: float,
    ) -> dict:
        if not daily_returns:
            return {}

        final_equity = daily_returns[-1].total_equity
        total_return = (final_equity - initial_capital) / initial_capital

        # Annualized return
        n_days = len(daily_returns)
        if n_days > 1:
            annualized_return = (1 + total_return) ** (252 / n_days) - 1
        else:
            annualized_return = 0.0

        # Max drawdown
        peak = initial_capital
        max_drawdown = 0.0
        for dr in daily_returns:
            if dr.total_equity > peak:
                peak = dr.total_equity
            drawdown = (peak - dr.total_equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Sharpe ratio (assuming risk-free rate = 0)
        returns = [dr.daily_return for dr in daily_returns if dr.daily_return is not None]
        if len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            std_return = math.sqrt(
                sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            )
            sharpe_ratio = (avg_return / std_return * math.sqrt(252)) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0

        # Win rate and profit/loss ratio
        sell_trades = [t for t in trades if t.direction == "sell" and t.realized_pnl is not None]
        if sell_trades:
            winning = [t for t in sell_trades if t.realized_pnl > 0]
            losing = [t for t in sell_trades if t.realized_pnl <= 0]
            win_rate = len(winning) / len(sell_trades)

            avg_win = sum(t.realized_pnl for t in winning) / len(winning) if winning else 0.0
            avg_loss = abs(sum(t.realized_pnl for t in losing) / len(losing)) if losing else 0.0
            profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float("inf")
        else:
            win_rate = 0.0
            profit_loss_ratio = 0.0

        return {
            "initial_capital": initial_capital,
            "final_equity": round(final_equity, 2),
            "total_return": round(total_return, 6),
            "annualized_return": round(annualized_return, 6),
            "max_drawdown": round(max_drawdown, 6),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "win_rate": round(win_rate, 4),
            "profit_loss_ratio": round(profit_loss_ratio, 4),
            "total_trades": len(trades),
            "trading_days": n_days,
        }
