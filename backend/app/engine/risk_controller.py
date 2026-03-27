from __future__ import annotations

from dataclasses import dataclass

from app.engine.position_manager import PositionManager


@dataclass
class RiskSignal:
    """Signal emitted when a risk condition is triggered."""

    action: str  # "sell"
    reason: str  # "stop_loss" | "take_profit" | "trailing_stop"


class RiskController:
    """Evaluates risk conditions against current price and position.

    All percentage parameters can be None (disabled). When set, they
    represent positive percentages (e.g. 5.0 means 5%).

    Check priority: stop_loss > trailing_stop > take_profit.
    First triggered condition wins.
    """

    def __init__(
        self,
        stop_loss_pct: float | None = None,
        take_profit_pct: float | None = None,
        trailing_stop_pct: float | None = None,
    ):
        self._stop_loss_pct = stop_loss_pct
        self._take_profit_pct = take_profit_pct
        self._trailing_stop_pct = trailing_stop_pct

    def check(
        self, current_price: float, position_manager: PositionManager
    ) -> RiskSignal | None:
        """Evaluate risk conditions for the current price.

        Returns:
            RiskSignal if a condition is triggered, None otherwise.
        """
        if position_manager.holding_quantity <= 0:
            return None

        avg_cost = position_manager.average_cost
        if avg_cost <= 0:
            return None

        # 1. Stop-loss: price dropped below threshold from average cost
        if self._stop_loss_pct is not None:
            pnl_pct = (current_price - avg_cost) / avg_cost
            if pnl_pct <= -(self._stop_loss_pct / 100.0):
                return RiskSignal(action="sell", reason="stop_loss")

        # 2. Trailing stop: price dropped from highest observed price
        if self._trailing_stop_pct is not None:
            highest = position_manager.highest_price
            if highest > 0:
                drop_pct = (highest - current_price) / highest
                if drop_pct >= (self._trailing_stop_pct / 100.0):
                    return RiskSignal(action="sell", reason="trailing_stop")

        # 3. Take-profit: price rose above threshold from average cost
        if self._take_profit_pct is not None:
            pnl_pct = (current_price - avg_cost) / avg_cost
            if pnl_pct >= (self._take_profit_pct / 100.0):
                return RiskSignal(action="sell", reason="take_profit")

        return None
