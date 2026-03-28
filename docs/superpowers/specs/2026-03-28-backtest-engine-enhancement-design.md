# Backtest Engine Enhancement Design Spec

## Goal

Enhance the backtesting engine with risk management (stop-loss, take-profit, trailing stop), dynamic position sizing, multi-stock backtesting (independent batch + equal-weight allocation portfolio modes), and partial position entry/exit (scaling in/out). Add simple/advanced mode UI toggle.

## Scope

### Engine
- Position Manager: dynamic sizing, cost tracking, commission/tax, scale in/out
- Risk Controller: stop-loss, take-profit, trailing stop (overrides strategy signals, returns specific reason)
- BacktestRunner refactor: integrate PositionManager + RiskController into day loop
- BatchRunner: run strategy independently on N stocks, aggregate results
- PortfolioRunner: equal-weight allocation across N stocks, combined equity tracking

### Data Model
- Backtest table: add mode, stock_ids, risk_params columns; make stock_id nullable
- BacktestTrade table: add reason column
- BacktestDailyReturn table: add stock_id column for per-stock tracking
- Alembic migration

### API
- Expand POST /backtests/ to accept mode, stock_ids, risk_params
- Expand GET /backtests/{id} response for multi-stock results
- Limit max stocks to 20

### Frontend
- Simple/Advanced mode toggle on backtest creation page
- Multi-stock input with autocomplete
- Risk parameter inputs
- Batch results: summary + per-stock tabs + overlay chart
- Portfolio results: combined equity curve, allocation pie chart
- Update TypeScript types and Zod schemas

---

## Architecture

### Engine Components

#### PositionManager

Manages all open positions for a single stock within a backtest. Handles commission and tax.

Responsibilities:
- Calculate order quantity based on `position_size_pct` of available capital
- Round to lot size (1000 shares for TW market)
- Deduct commission on buy: `price * quantity * (1 + commission_rate)`
- Credit after sell: `price * quantity * (1 - commission_rate - tax_rate)`
- Track each position's entry price, quantity, and highest price since entry
- Support scale-in: add to existing position (up to `max_scale_in_times`)
- Support scale-out: partial sell (reduce position by quantity)
- Calculate realized P&L on each sell (FIFO cost basis)
- Reset `scale_in_count` to 0 when `holding_quantity` drops to 0 (full exit)

Interface:
```python
class PositionManager:
    def __init__(
        self,
        initial_capital: float,
        position_size_pct: float,
        max_scale_in: int,
        commission_rate: float = 0.001425,  # 0.1425%
        tax_rate: float = 0.003,  # 0.3% sell only
        lot_size: int = 1000,
    )
    def buy(self, price: float, date: date, quantity: int | None = None) -> Trade | None
        # quantity=None → auto-size from position_size_pct
        # quantity=int → use explicit quantity (for backward compat)
        # returns None if insufficient capital or quantity rounds to 0
    def sell(self, price: float, date: date, quantity: int | None = None) -> Trade | None
        # quantity=None → sell all
    def update_high(self, price: float)  # track highest price for trailing stop
    @property
    def holding_quantity(self) -> int
    @property
    def average_cost(self) -> float
    @property
    def highest_price(self) -> float
    @property
    def available_capital(self) -> float
    @property
    def total_equity(self) -> float  # cash + holdings at market value
    @property
    def scale_in_count(self) -> int  # resets to 0 after full exit
```

**Backward compatibility:** When `position_size_pct=100` and `allow_scale_in=false` (defaults), the behavior matches the existing engine: buy with all available capital, sell all on SELL signal. The optional `quantity` parameter allows strategies that return specific quantities to still work.

#### RiskController

Evaluates risk conditions BEFORE strategy signal is processed. Returns specific trigger reason.

Interface:
```python
class RiskSignal:
    action: str  # "sell"
    reason: str  # "stop_loss" | "take_profit" | "trailing_stop"

class RiskController:
    def __init__(self, stop_loss_pct: float | None, take_profit_pct: float | None, trailing_stop_pct: float | None)
    def check(self, current_price: float, position: PositionManager) -> RiskSignal | None
```

Evaluation priority: stop-loss > trailing stop > take-profit (first trigger wins).
Returns `None` if no condition triggered or all params are `None` (disabled).

#### BacktestRunner Refactored Day Loop

```
for each trading_date:
    current_price = prices[date].close_price
    if current_price is None:
        continue  # skip days with no data

    # 1. Update position tracking
    position_manager.update_high(current_price)

    # 2. Risk check (overrides strategy)
    risk_signal = risk_controller.check(current_price, position_manager)

    if risk_signal and position_manager.holding_quantity > 0:
        trade = position_manager.sell(current_price, date)
        record_trade(trade, reason=risk_signal.reason)
    else:
        # 3. Strategy signal
        signal = strategy.on_data(date, market_data)

        if signal == BUY:
            if allow_scale_in and position_manager.scale_in_count < max_scale_in:
                trade = position_manager.buy(current_price, date)
            elif position_manager.holding_quantity == 0:
                trade = position_manager.buy(current_price, date)
            if trade:
                record_trade(trade, reason="strategy")
        elif signal == SELL and position_manager.holding_quantity > 0:
            trade = position_manager.sell(current_price, date)
            if trade:
                record_trade(trade, reason="strategy")

    # 4. Record daily equity
    record_daily_equity(date, position_manager.total_equity)
```

#### BatchRunner

Runs a single strategy across multiple stocks independently.

```python
class BatchRunner:
    async def run(self, backtest_id: int):
        backtest = load_backtest(backtest_id)
        results = []
        for stock_id in backtest.stock_ids:
            runner = BacktestRunner(...)
            result = await runner.run_single(stock_id, backtest)
            results.append(result)
        save_batch_results(backtest_id, results)
        calculate_summary_metrics(backtest_id, results)
```

Each stock gets its own capital pool (initial_capital applied per stock). Summary metrics: average return, best/worst stock, win rate across stocks.

Per-stock daily returns stored with `stock_id` in `BacktestDailyReturn`.

#### PortfolioRunner

Equal-weight allocation across multiple stocks. Each stock gets `initial_capital / N` and manages its allocation independently. This is fixed allocation (no rebalancing or cross-stock capital sharing).

```python
class PortfolioRunner:
    async def run(self, backtest_id: int):
        backtest = load_backtest(backtest_id)
        stock_ids = backtest.stock_ids
        per_stock_capital = backtest.initial_capital / len(stock_ids)

        positions = {sid: PositionManager(per_stock_capital, ...) for sid in stock_ids}
        risk_controllers = {sid: RiskController(...) for sid in stock_ids}

        # trading_dates = union of all stocks' trading dates
        trading_dates = get_union_trading_dates(stock_ids, start_date, end_date)

        for date in trading_dates:
            for stock_id in stock_ids:
                price = get_price(stock_id, date)
                if price is None:
                    continue  # stock has no data for this date (halted, etc.)

                pm = positions[stock_id]
                rc = risk_controllers[stock_id]
                pm.update_high(price)

                risk_signal = rc.check(price, pm)
                if risk_signal and pm.holding_quantity > 0:
                    trade = pm.sell(price, date)
                    record_trade(trade, stock_id=stock_id, reason=risk_signal.reason)
                else:
                    signal = strategy.on_data(date, market_data, stock_id)
                    # ... same logic as BacktestRunner

            # Record combined equity (portfolio level)
            total = sum(pm.total_equity for pm in positions.values())
            record_daily_equity(date, total, stock_id=None)  # NULL = portfolio level

            # Record per-stock equity
            for sid, pm in positions.items():
                record_daily_equity(date, pm.total_equity, stock_id=sid)
```

**Note:** This is equal-weight fixed allocation, not dynamic rebalancing. Freed capital from selling Stock A stays in Stock A's allocation. Future enhancement could add a `CapitalPool` for true shared capital.

### Celery Task Update

`run_backtest_task` dispatches to the correct runner based on `mode`:
- `"single"` → BacktestRunner (existing, refactored)
- `"batch"` → BatchRunner
- `"portfolio"` → PortfolioRunner

---

## Data Model Changes

### Backtest table changes

```sql
ALTER TABLE backtests ALTER COLUMN stock_id DROP NOT NULL;
ALTER TABLE backtests ADD COLUMN mode VARCHAR(10) DEFAULT 'single';
ALTER TABLE backtests ADD COLUMN stock_ids JSONB;
ALTER TABLE backtests ADD COLUMN risk_params JSONB;
```

- `stock_id`: now nullable. Single mode uses this. Batch/portfolio set this to NULL.
- `mode`: "single" | "batch" | "portfolio"
- `stock_ids`: `["2330", "2317", "2454"]` (for batch/portfolio, NULL for single)
- `risk_params`: JSONB with risk settings

Update model:
```python
stock_id: Mapped[str | None] = mapped_column(String(10), ForeignKey("stocks.stock_id"), nullable=True)
mode: Mapped[str] = mapped_column(String(10), default="single")
stock_ids: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
risk_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

### BacktestTrade table changes

```sql
ALTER TABLE backtest_trades ADD COLUMN reason VARCHAR(20) DEFAULT 'strategy';
```
Values: "strategy", "stop_loss", "take_profit", "trailing_stop"

### BacktestDailyReturn table changes

```sql
ALTER TABLE backtest_daily_returns ADD COLUMN stock_id VARCHAR(10);
```
- NULL = single mode or portfolio-level combined equity
- Non-null = per-stock equity in batch/portfolio mode

### Risk params defaults

When `risk_params` is NULL or empty, use:
```json
{
  "stop_loss_pct": null,
  "take_profit_pct": null,
  "trailing_stop_pct": null,
  "position_size_pct": 100.0,
  "allow_scale_in": false,
  "max_scale_in_times": 0
}
```
`null` means disabled (no stop-loss/take-profit/trailing stop).
`position_size_pct: 100` = use all available capital (matches existing behavior).

---

## API Changes

### POST /api/v1/backtests/

Request body expansion:
```json
{
  "strategy_id": 1,
  "stock_id": "2330",
  "stock_ids": ["2330", "2317"],
  "start_date": "2025-01-01",
  "end_date": "2026-01-01",
  "initial_capital": 1000000,
  "mode": "single",
  "risk_params": {
    "stop_loss_pct": 5.0,
    "take_profit_pct": 10.0,
    "trailing_stop_pct": 3.0,
    "position_size_pct": 30.0,
    "allow_scale_in": true,
    "max_scale_in_times": 3
  }
}
```

Validation:
- `mode="single"`: `stock_id` required, `stock_ids` ignored
- `mode="batch"` or `"portfolio"`: `stock_ids` required (2-20 items), `stock_id` ignored
- `stock_ids` max 20 stocks (prevent excessive load)
- `risk_params`: all fields optional, validated ranges (pct > 0 when set, max_scale_in >= 0)
- `mode` defaults to `"single"` when not provided

### GET /api/v1/backtests/{id}

Response expansion:
- Add `mode`, `stock_ids`, `risk_params` to response
- `trades`: add `reason` field per trade
- For batch mode: add `per_stock_results` object keyed by stock_id, each containing metrics + daily_returns
- For portfolio mode: add `portfolio_daily_returns` (combined) + `per_stock_daily_returns` keyed by stock_id

---

## Frontend Changes

### TypeScript types & Zod schemas

Update `frontend/src/types/index.ts` and `frontend/src/lib/schemas.ts`:
- `Backtest` type: add `mode`, `stock_ids`, `risk_params`
- `BacktestTrade` type: add `reason`
- Add `RiskParams` type
- Add `PerStockResult` type for batch mode
- Update Zod schemas accordingly

### New Backtest Page (/backtests/new)

**Simple Mode (default):**
- Same as current: strategy dropdown, single stock input, date range, capital
- Small link/button: "切換進階模式"

**Advanced Mode:**
- Section 1: Strategy (same dropdown)
- Section 2: 回測模式
  - Radio: 個股 / 批次比較 / 投資組合
  - 個股: single stock input (same as now)
  - 批次/組合: multi-stock input (add button, each with autocomplete, remove button, max 20)
- Section 3: 風控設定
  - 停損 %: number input (placeholder "不設定")
  - 停利 %: number input
  - 移動停損 %: number input
  - 每次下單比例 %: number input (default 100)
- Section 4: 分批進出
  - Toggle: 允許加碼 (default off)
  - 最大加碼次數: number (shown when toggle on, default 3)
- Section 5: 日期範圍 + 初始資金 (same as now)
- Link: "切換簡易模式"

### Backtest Detail Page (/backtests/[id])

**Single mode:** Same as current + show risk_params card + trade reason column in trades table

**Batch mode:**
- Summary card: average return, best/worst stock, overall win rate
- Comparison chart: overlay equity curves of all stocks (Recharts LineChart with multiple Line)
- Tab bar: each stock as a tab
- Each tab: metrics cards + equity curve + trades table (same layout as single)

**Portfolio mode:**
- Portfolio metrics cards (combined return, drawdown, Sharpe)
- Combined equity curve
- Allocation pie chart (Recharts PieChart, equal weight)
- Per-stock contribution table
- All trades table with stock_id + reason columns

---

## File Structure

### New files
| File | Responsibility |
|------|----------------|
| `backend/app/engine/position_manager.py` | Position tracking, order sizing, commission/tax, scale in/out |
| `backend/app/engine/risk_controller.py` | Stop-loss, take-profit, trailing stop with specific reason |
| `backend/app/engine/batch_runner.py` | Independent multi-stock backtesting |
| `backend/app/engine/portfolio_runner.py` | Equal-weight allocation multi-stock backtesting |
| `backend/alembic/versions/xxx_backtest_engine_enhancement.py` | Migration |

### Modified files
| File | Changes |
|------|---------|
| `backend/app/engine/backtest_runner.py` | Integrate PositionManager + RiskController, refactor day loop |
| `backend/app/api/backtests.py` | Accept new fields, dispatch to correct runner, validation |
| `backend/app/models/backtest.py` | Add mode, stock_ids, risk_params columns; stock_id nullable; trade reason; daily_return stock_id |
| `backend/app/tasks/backtest_task.py` | Route to correct runner by mode |
| `frontend/src/types/index.ts` | Add new types (RiskParams, mode, etc.) |
| `frontend/src/lib/schemas.ts` | Update Zod schemas |
| `frontend/src/app/(dashboard)/backtests/new/page.tsx` | Simple/Advanced toggle, multi-stock, risk params UI |
| `frontend/src/app/(dashboard)/backtests/[backtestId]/page.tsx` | Batch/portfolio result views, trade reason column |

**Note:** `backend/app/engine/strategies.py` does NOT need modification. Strategies remain stateless and return BUY/SELL/HOLD. Scale-in logic is handled externally by the day loop + PositionManager.

---

## Testing

### Engine tests
- PositionManager: buy/sell/scale-in, capital with commission/tax deduction, lot rounding, FIFO cost, scale_in_count reset after full exit
- PositionManager backward compat: position_size_pct=100 matches old behavior
- RiskController: stop-loss triggers with correct reason, take-profit, trailing stop, null params returns None
- BacktestRunner: risk controller overrides strategy signal, scale-in flow, missing price dates skipped
- BatchRunner: runs N stocks independently, per-stock daily returns stored with stock_id
- PortfolioRunner: equal-weight allocation, combined + per-stock equity, skip missing price dates

### API tests
- Create single/batch/portfolio backtests
- Validation: missing stock_ids for batch, stock_ids > 20 rejected, invalid risk_params
- Backward compat: omit mode/risk_params → defaults to single with no risk management
- Response includes new fields

### Frontend tests
- Simple/Advanced mode toggle preserves input state
- Multi-stock add/remove, max 20 limit
- Risk params sent correctly in API request
- Batch results render tabs + overlay chart
- Portfolio results render combined chart + pie chart
- Trade reason column shows correct labels
- Existing backtests (no mode) display correctly

### Backward compatibility
- Existing backtests (mode=NULL → treated as "single") load and display correctly
- Existing trades (reason=NULL → treated as "strategy") display correctly
- API without mode/risk_params works exactly as before
