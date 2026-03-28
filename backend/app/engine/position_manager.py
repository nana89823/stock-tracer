from __future__ import annotations

from datetime import date


class PositionManager:
    """Manages positions for a single stock within a backtest.

    Tracks cash, holdings (FIFO cost basis), commission/tax, and supports
    dynamic position sizing and scale-in/out.
    """

    def __init__(
        self,
        initial_capital: float,
        position_size_pct: float = 100.0,
        max_scale_in: int = 0,
        commission_rate: float = 0.001425,
        tax_rate: float = 0.003,
        lot_size: int = 1000,
    ):
        self._cash = initial_capital
        self._initial_capital = initial_capital
        self._position_size_pct = position_size_pct
        self._max_scale_in = max_scale_in
        self._commission_rate = commission_rate
        self._tax_rate = tax_rate
        self._lot_size = lot_size

        # FIFO cost entries: list of {"price": float, "quantity": int}
        self._cost_entries: list[dict] = []
        self._highest_price: float = 0.0
        self._scale_in_count: int = 0

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def buy(
        self, price: float, trade_date: date, quantity: int | None = None
    ) -> dict | None:
        """Execute a buy order.

        Args:
            price: Execution price per share.
            trade_date: Trade date.
            quantity: Explicit share count. If None, auto-size from
                      position_size_pct of available_capital, rounded
                      down to lot_size.

        Returns:
            Trade dict or None if insufficient capital / zero quantity.
        """
        if quantity is None:
            budget = self._cash * (self._position_size_pct / 100.0)
            # price * qty * (1 + commission) <= budget
            raw_qty = budget / (price * (1 + self._commission_rate))
            quantity = int(raw_qty // self._lot_size) * self._lot_size
        else:
            # Round explicit quantity to lot_size
            quantity = int(quantity // self._lot_size) * self._lot_size

        if quantity <= 0:
            return None

        cost = quantity * price
        commission = cost * self._commission_rate
        total_cost = cost + commission

        if total_cost > self._cash:
            return None

        # Deduct from cash
        self._cash -= total_cost

        # Track FIFO cost entry
        self._cost_entries.append({"price": price, "quantity": quantity})

        # Update highest price tracking for trailing stop
        if price > self._highest_price:
            self._highest_price = price

        # Increment scale-in count (first buy counts as 0, subsequent as 1+)
        if self.holding_quantity - quantity > 0:
            # Had existing holdings before this buy -> this is a scale-in
            pass
        # After adding quantity above via _cost_entries, holding_quantity
        # already includes this buy. If prior holding was > 0, it's a scale-in.
        prior_holding = self.holding_quantity - quantity
        if prior_holding > 0:
            self._scale_in_count += 1

        return {
            "date": trade_date,
            "direction": "buy",
            "price": price,
            "quantity": quantity,
            "commission": commission,
            "tax": 0.0,
            "realized_pnl": None,
        }

    def sell(
        self, price: float, trade_date: date, quantity: int | None = None
    ) -> dict | None:
        """Execute a sell order.

        Args:
            price: Execution price per share.
            trade_date: Trade date.
            quantity: Shares to sell. If None, sell all holdings.

        Returns:
            Trade dict or None if no holdings.
        """
        current_holding = self.holding_quantity
        if current_holding <= 0:
            return None

        if quantity is None:
            quantity = current_holding
        else:
            quantity = int(quantity // self._lot_size) * self._lot_size
            quantity = min(quantity, current_holding)

        if quantity <= 0:
            return None

        # Calculate realized P&L using FIFO cost basis
        remaining_to_sell = quantity
        total_cost_basis = 0.0

        new_entries: list[dict] = []
        for entry in self._cost_entries:
            if remaining_to_sell <= 0:
                new_entries.append(entry)
                continue

            if entry["quantity"] <= remaining_to_sell:
                # Consume entire entry
                total_cost_basis += entry["price"] * entry["quantity"]
                remaining_to_sell -= entry["quantity"]
            else:
                # Partial consumption
                total_cost_basis += entry["price"] * remaining_to_sell
                new_entries.append({
                    "price": entry["price"],
                    "quantity": entry["quantity"] - remaining_to_sell,
                })
                remaining_to_sell = 0

        self._cost_entries = new_entries

        proceeds = quantity * price
        commission = proceeds * self._commission_rate
        tax = proceeds * self._tax_rate
        net_proceeds = proceeds - commission - tax

        realized_pnl = net_proceeds - total_cost_basis

        # Credit cash
        self._cash += net_proceeds

        # Reset scale_in_count and highest_price if fully exited
        if self.holding_quantity == 0:
            self._scale_in_count = 0
            self._highest_price = 0.0

        return {
            "date": trade_date,
            "direction": "sell",
            "price": price,
            "quantity": quantity,
            "commission": commission,
            "tax": tax,
            "realized_pnl": realized_pnl,
        }

    def update_high(self, price: float) -> None:
        """Track highest price since last entry (for trailing stop)."""
        if self.holding_quantity > 0 and price > self._highest_price:
            self._highest_price = price

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def holding_quantity(self) -> int:
        """Total shares currently held."""
        return sum(e["quantity"] for e in self._cost_entries)

    @property
    def average_cost(self) -> float:
        """Weighted average cost per share of current holdings."""
        total_qty = self.holding_quantity
        if total_qty == 0:
            return 0.0
        total_cost = sum(e["price"] * e["quantity"] for e in self._cost_entries)
        return total_cost / total_qty

    @property
    def highest_price(self) -> float:
        """Highest price observed since last entry."""
        return self._highest_price

    @property
    def available_capital(self) -> float:
        """Cash available for new orders."""
        return self._cash

    def get_total_equity(self, current_price: float) -> float:
        """Total equity = cash + holdings at current market price."""
        return self._cash + self.holding_quantity * current_price

    @property
    def scale_in_count(self) -> int:
        """Number of scale-in buys since last full exit."""
        return self._scale_in_count
