from datetime import date

from app.engine.base_strategy import BaseStrategy, MarketData, Signal, SignalType


class MACrossoverStrategy(BaseStrategy):
    """Moving Average Crossover Strategy.

    Generates BUY when the short-term MA crosses above the long-term MA,
    and SELL when it crosses below.
    """

    @property
    def name(self) -> str:
        return "ma_crossover"

    @property
    def default_params(self) -> dict:
        return {"short_window": 5, "long_window": 20}

    def on_data(self, current_date: date, data: MarketData) -> Signal:
        short_window = self.params.get("short_window", self.default_params["short_window"])
        long_window = self.params.get("long_window", self.default_params["long_window"])

        # Filter prices up to current_date
        prices = [p for p in data.prices if p["date"] <= current_date]
        if len(prices) < long_window + 1:
            return Signal(SignalType.HOLD, prices[-1]["stock_id"] if prices else "", current_date)

        stock_id = prices[-1]["stock_id"]
        closes = [p["close_price"] for p in prices]

        # Current MAs
        short_ma = sum(closes[-short_window:]) / short_window
        long_ma = sum(closes[-long_window:]) / long_window

        # Previous MAs (yesterday)
        prev_closes = closes[:-1]
        prev_short_ma = sum(prev_closes[-short_window:]) / short_window
        prev_long_ma = sum(prev_closes[-long_window:]) / long_window

        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            return Signal(
                SignalType.BUY, stock_id, current_date,
                quantity=1000,
                reason=f"Short MA({short_window}) crossed above Long MA({long_window})",
            )
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            return Signal(
                SignalType.SELL, stock_id, current_date,
                quantity=1000,
                reason=f"Short MA({short_window}) crossed below Long MA({long_window})",
            )

        return Signal(SignalType.HOLD, stock_id, current_date)


class InstitutionalFollowStrategy(BaseStrategy):
    """Follow institutional investors (foreign, trust, dealer).

    Generates BUY when the chosen institution has net-bought for N consecutive days,
    and SELL when net-sold for N consecutive days.
    """

    @property
    def name(self) -> str:
        return "institutional_follow"

    @property
    def default_params(self) -> dict:
        return {"institution": "foreign", "consecutive_days": 3}

    def on_data(self, current_date: date, data: MarketData) -> Signal:
        institution = self.params.get("institution", self.default_params["institution"])
        consecutive_days = self.params.get(
            "consecutive_days", self.default_params["consecutive_days"]
        )

        # Map institution to the net column in chip data
        net_field_map = {
            "foreign": "foreign_net",
            "trust": "trust_net",
            "dealer": "dealer_net",
        }
        net_field = net_field_map.get(institution, "foreign_net")

        chips = [c for c in data.chips if c["date"] <= current_date]
        if len(chips) < consecutive_days:
            stock_id = chips[-1]["stock_id"] if chips else ""
            return Signal(SignalType.HOLD, stock_id, current_date)

        stock_id = chips[-1]["stock_id"]
        recent = chips[-consecutive_days:]

        all_buy = all(c[net_field] > 0 for c in recent)
        all_sell = all(c[net_field] < 0 for c in recent)

        if all_buy:
            return Signal(
                SignalType.BUY, stock_id, current_date,
                quantity=1000,
                reason=f"{institution} net-bought for {consecutive_days} consecutive days",
            )
        elif all_sell:
            return Signal(
                SignalType.SELL, stock_id, current_date,
                quantity=1000,
                reason=f"{institution} net-sold for {consecutive_days} consecutive days",
            )

        return Signal(SignalType.HOLD, stock_id, current_date)


class MajorHolderStrategy(BaseStrategy):
    """Major holder shareholding change strategy.

    Generates BUY when the holding ratio of a specified level increases
    beyond a threshold, and SELL when it decreases.
    """

    @property
    def name(self) -> str:
        return "major_holder"

    @property
    def default_params(self) -> dict:
        return {"threshold_level": 15, "change_pct": 0.5}

    def on_data(self, current_date: date, data: MarketData) -> Signal:
        threshold_level = self.params.get(
            "threshold_level", self.default_params["threshold_level"]
        )
        change_pct = self.params.get("change_pct", self.default_params["change_pct"])

        # Filter holders data up to current_date for the specified level
        holders = [
            h for h in data.holders
            if h["date"] <= current_date and h["holding_level"] == threshold_level
        ]

        if len(holders) < 2:
            stock_id = holders[-1]["stock_id"] if holders else ""
            return Signal(SignalType.HOLD, stock_id, current_date)

        stock_id = holders[-1]["stock_id"]
        current_ratio = holders[-1]["holding_ratio"]
        prev_ratio = holders[-2]["holding_ratio"]
        change = current_ratio - prev_ratio

        if change >= change_pct:
            return Signal(
                SignalType.BUY, stock_id, current_date,
                quantity=1000,
                reason=f"Major holder (level {threshold_level}) ratio increased by {change:.2f}%",
            )
        elif change <= -change_pct:
            return Signal(
                SignalType.SELL, stock_id, current_date,
                quantity=1000,
                reason=f"Major holder (level {threshold_level}) ratio decreased by {abs(change):.2f}%",
            )

        return Signal(SignalType.HOLD, stock_id, current_date)


class MarginIndicatorStrategy(BaseStrategy):
    """Margin trading indicator strategy.

    Generates BUY when margin utilization is low and short utilization is high
    (potential short squeeze). Generates SELL for the opposite scenario.
    """

    @property
    def name(self) -> str:
        return "margin_indicator"

    @property
    def default_params(self) -> dict:
        return {"margin_ratio_threshold": 0.25, "short_ratio_threshold": 0.1}

    def on_data(self, current_date: date, data: MarketData) -> Signal:
        margin_ratio_threshold = self.params.get(
            "margin_ratio_threshold", self.default_params["margin_ratio_threshold"]
        )
        short_ratio_threshold = self.params.get(
            "short_ratio_threshold", self.default_params["short_ratio_threshold"]
        )

        margin_data = [m for m in data.margin if m["date"] <= current_date]
        if not margin_data:
            return Signal(SignalType.HOLD, "", current_date)

        latest = margin_data[-1]
        stock_id = latest["stock_id"]

        # Calculate utilization ratios
        margin_limit = latest.get("margin_limit", 0)
        short_limit = latest.get("short_limit", 0)

        if margin_limit == 0 or short_limit == 0:
            return Signal(SignalType.HOLD, stock_id, current_date)

        margin_ratio = latest["margin_balance"] / margin_limit
        short_ratio = latest["short_balance"] / short_limit

        # Low margin + high short => potential short squeeze => BUY
        if margin_ratio < margin_ratio_threshold and short_ratio > short_ratio_threshold:
            return Signal(
                SignalType.BUY, stock_id, current_date,
                quantity=1000,
                reason=(
                    f"Margin ratio {margin_ratio:.2%} < {margin_ratio_threshold:.2%}, "
                    f"Short ratio {short_ratio:.2%} > {short_ratio_threshold:.2%}"
                ),
            )
        # High margin + low short => bearish signal => SELL
        elif margin_ratio > margin_ratio_threshold and short_ratio < short_ratio_threshold:
            return Signal(
                SignalType.SELL, stock_id, current_date,
                quantity=1000,
                reason=(
                    f"Margin ratio {margin_ratio:.2%} > {margin_ratio_threshold:.2%}, "
                    f"Short ratio {short_ratio:.2%} < {short_ratio_threshold:.2%}"
                ),
            )

        return Signal(SignalType.HOLD, stock_id, current_date)


# Registry of all built-in strategies
BUILTIN_STRATEGIES = {
    "ma_crossover": {
        "cls": MACrossoverStrategy,
        "name": "MA Crossover",
        "description": "Moving Average Crossover: BUY when short MA crosses above long MA, SELL when below.",
        "default_params": MACrossoverStrategy().default_params,
    },
    "institutional_follow": {
        "cls": InstitutionalFollowStrategy,
        "name": "Institutional Follow",
        "description": "Follow institutional investors: BUY/SELL based on consecutive net-buy/sell days.",
        "default_params": InstitutionalFollowStrategy().default_params,
    },
    "major_holder": {
        "cls": MajorHolderStrategy,
        "name": "Major Holder",
        "description": "Major holder shareholding change: BUY when large holders increase, SELL when decrease.",
        "default_params": MajorHolderStrategy().default_params,
    },
    "margin_indicator": {
        "cls": MarginIndicatorStrategy,
        "name": "Margin Indicator",
        "description": "Margin trading indicator: BUY on potential short squeeze, SELL on bearish margin signal.",
        "default_params": MarginIndicatorStrategy().default_params,
    },
}
