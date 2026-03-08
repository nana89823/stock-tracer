import math
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.base_strategy import BaseStrategy, MarketData, SignalType
from app.engine.strategies import BUILTIN_STRATEGIES
from app.models.backtest import Backtest, BacktestDailyReturn, BacktestTrade
from app.models.major_holders import MajorHolders
from app.models.margin_trading import MarginTrading
from app.models.raw_chip import RawChip
from app.models.raw_price import RawPrice
from app.models.strategy import Strategy


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

            # 3. Load market data
            market_data = await self._load_market_data(
                backtest.stock_id, backtest.start_date, backtest.end_date
            )

            # 4. Run simulation
            run_result = self._simulate(
                strategy=strategy,
                stock_id=backtest.stock_id,
                market_data=market_data,
                initial_capital=backtest.initial_capital,
                backtest_id=backtest.id,
            )

            # 5. Save trades and daily returns
            for trade in run_result["trades"]:
                self.db.add(trade)
            for dr in run_result["daily_returns"]:
                self.db.add(dr)

            # 6. Update backtest record
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

    def _simulate(
        self,
        strategy: BaseStrategy,
        stock_id: str,
        market_data: MarketData,
        initial_capital: float,
        backtest_id: int,
    ) -> dict:
        cash = initial_capital
        holdings: dict[str, int] = {}  # stock_id -> quantity
        avg_cost: dict[str, float] = {}  # stock_id -> average cost per share
        trades: list[BacktestTrade] = []
        daily_returns: list[BacktestDailyReturn] = []
        prev_equity = initial_capital

        # Get trading dates within simulation range
        trading_dates = sorted(set(
            p["date"] for p in market_data.prices
            if p["date"] >= market_data.prices[0]["date"]
        ))

        # Find start_date index: we need the first date that appears in our price data
        # and is within the backtest range
        start_idx = None
        for i, d in enumerate(trading_dates):
            # Find first date in the trading range where strategy can operate
            if start_idx is None:
                start_idx = i

        if start_idx is None:
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

            # Get signal from strategy (only data up to current_date is visible)
            signal = strategy.on_data(current_date, market_data)

            current_holding = holdings.get(stock_id, 0)

            if signal.signal_type == SignalType.BUY:
                quantity = (signal.quantity // self.LOT_SIZE) * self.LOT_SIZE
                if quantity <= 0:
                    quantity = self.LOT_SIZE

                cost = quantity * close_price
                commission = cost * self.COMMISSION_RATE

                if cash >= cost + commission:
                    cash -= cost + commission
                    prev_holding = holdings.get(stock_id, 0)
                    prev_cost = avg_cost.get(stock_id, 0.0)
                    new_holding = prev_holding + quantity
                    avg_cost[stock_id] = (
                        (prev_cost * prev_holding + cost) / new_holding
                        if new_holding > 0 else 0.0
                    )
                    holdings[stock_id] = new_holding

                    trades.append(BacktestTrade(
                        backtest_id=backtest_id,
                        trade_date=current_date,
                        stock_id=stock_id,
                        direction="buy",
                        price=close_price,
                        quantity=quantity,
                        commission=commission,
                        tax=0.0,
                        realized_pnl=None,
                    ))

            elif signal.signal_type == SignalType.SELL and current_holding > 0:
                quantity = min(
                    (signal.quantity // self.LOT_SIZE) * self.LOT_SIZE,
                    current_holding,
                )
                if quantity <= 0:
                    quantity = min(self.LOT_SIZE, current_holding)

                proceeds = quantity * close_price
                commission = proceeds * self.COMMISSION_RATE
                tax = proceeds * self.TAX_RATE

                cost_basis = avg_cost.get(stock_id, 0.0) * quantity
                realized_pnl = proceeds - commission - tax - cost_basis

                cash += proceeds - commission - tax
                holdings[stock_id] = current_holding - quantity

                if holdings[stock_id] == 0:
                    avg_cost.pop(stock_id, None)

                trades.append(BacktestTrade(
                    backtest_id=backtest_id,
                    trade_date=current_date,
                    stock_id=stock_id,
                    direction="sell",
                    price=close_price,
                    quantity=quantity,
                    commission=commission,
                    tax=tax,
                    realized_pnl=realized_pnl,
                ))

            # Calculate daily portfolio value
            position_value = sum(
                qty * self._get_close(market_data.prices, sid, current_date)
                for sid, qty in holdings.items()
                if qty > 0
            )
            total_equity = cash + position_value
            daily_ret = (
                (total_equity - prev_equity) / prev_equity
                if prev_equity > 0 else None
            )

            daily_returns.append(BacktestDailyReturn(
                backtest_id=backtest_id,
                date=current_date,
                position_value=position_value,
                cash=cash,
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
