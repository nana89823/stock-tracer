export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface Stock {
  stock_id: string;
  stock_name: string;
  market_type: string;
}

export interface RawPrice {
  date: string;
  stock_id: string;
  stock_name: string;
  trade_volume: number;
  trade_value: number;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  price_change: number;
  transaction_count: number;
}

export interface RawChip {
  date: string;
  stock_id: string;
  stock_name: string;
  foreign_buy: number;
  foreign_sell: number;
  foreign_net: number;
  trust_buy: number;
  trust_sell: number;
  trust_net: number;
  dealer_net: number;
  total_net: number;
}

export interface MajorHolder {
  date: string;
  stock_id: string;
  holding_level: number;
  holder_count: number;
  share_count: number;
  holding_ratio: number;
}

export interface MarginTrading {
  date: string;
  stock_id: string;
  margin_buy: number;
  margin_sell: number;
  margin_cash_repay: number;
  margin_balance_prev: number;
  margin_balance: number;
  margin_limit: number;
  short_buy: number;
  short_sell: number;
  short_cash_repay: number;
  short_balance_prev: number;
  short_balance: number;
  short_limit: number;
  offset: number;
}

export interface BrokerTrading {
  date: string;
  stock_id: string;
  broker_id: string;
  broker_name: string;
  price: number;
  buy_volume: number;
  sell_volume: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Strategy {
  id: number;
  name: string;
  description: string | null;
  strategy_type: string;
  is_builtin: boolean;
  params: Record<string, unknown> | null;
}

export interface RiskParams {
  stop_loss_pct: number | null;
  take_profit_pct: number | null;
  trailing_stop_pct: number | null;
  position_size_pct: number;
  allow_scale_in: boolean;
  max_scale_in_times: number;
}

export interface BacktestTrade {
  id: number;
  trade_date: string;
  stock_id: string;
  direction: "buy" | "sell";
  price: number;
  quantity: number;
  commission: number;
  tax: number;
  realized_pnl: number | null;
  reason?: string | null;
}

export interface BacktestDailyReturn {
  date: string;
  position_value: number;
  cash: number;
  total_equity: number;
  daily_return: number | null;
  stock_id?: string | null;
}

export interface BacktestResult {
  total_return: number;
  annualized_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  profit_loss_ratio: number;
  total_trades: number;
  avg_holding_days: number;
  final_equity: number;
}

export interface PerStockResult {
  stock_id: string;
  metrics: BacktestResult;
}

export interface Backtest {
  id: number;
  strategy_id: number;
  stock_id: string | null;
  start_date: string;
  end_date: string;
  initial_capital: number;
  status: "pending" | "running" | "completed" | "failed";
  error_message: string | null;
  result: BacktestResult | null;
  created_at: string;
  completed_at: string | null;
  mode?: "single" | "batch" | "portfolio";
  stock_ids?: string[] | null;
  risk_params?: RiskParams | null;
  per_stock_results?: PerStockResult[] | null;
  trades?: BacktestTrade[];
  daily_returns?: BacktestDailyReturn[];
}
