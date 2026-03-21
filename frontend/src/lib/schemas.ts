/**
 * Zod schemas for API response validation.
 *
 * Usage:
 *   import { StockSchema, RawPriceListSchema } from "@/lib/schemas";
 *
 *   // Validate a single object:
 *   const stock = StockSchema.parse(res.data);
 *
 *   // Validate an array:
 *   const prices = RawPriceListSchema.parse(res.data);
 *
 *   // Safe parse (no throw):
 *   const result = StockSchema.safeParse(res.data);
 *   if (result.success) { console.log(result.data); }
 */

import { z } from "zod";

// --- User ---
export const UserSchema = z.object({
  id: z.number(),
  username: z.string(),
  email: z.string(),
  is_active: z.boolean(),
  created_at: z.string(),
});

// --- Stock ---
export const StockSchema = z.object({
  stock_id: z.string(),
  stock_name: z.string(),
  market_type: z.string(),
});
export const StockListSchema = z.array(StockSchema);

// --- RawPrice ---
export const RawPriceSchema = z.object({
  date: z.string(),
  stock_id: z.string(),
  stock_name: z.string(),
  trade_volume: z.number(),
  trade_value: z.number(),
  open_price: z.number(),
  high_price: z.number(),
  low_price: z.number(),
  close_price: z.number(),
  price_change: z.number(),
  transaction_count: z.number(),
});
export const RawPriceListSchema = z.array(RawPriceSchema);

// --- RawChip ---
export const RawChipSchema = z.object({
  date: z.string(),
  stock_id: z.string(),
  stock_name: z.string(),
  foreign_buy: z.number(),
  foreign_sell: z.number(),
  foreign_net: z.number(),
  trust_buy: z.number(),
  trust_sell: z.number(),
  trust_net: z.number(),
  dealer_net: z.number(),
  total_net: z.number(),
});
export const RawChipListSchema = z.array(RawChipSchema);

// --- MajorHolder ---
export const MajorHolderSchema = z.object({
  date: z.string(),
  stock_id: z.string(),
  holding_level: z.number(),
  holder_count: z.number(),
  share_count: z.number(),
  holding_ratio: z.number(),
});
export const MajorHolderListSchema = z.array(MajorHolderSchema);

// --- MarginTrading ---
export const MarginTradingSchema = z.object({
  date: z.string(),
  stock_id: z.string(),
  margin_buy: z.number(),
  margin_sell: z.number(),
  margin_cash_repay: z.number(),
  margin_balance_prev: z.number(),
  margin_balance: z.number(),
  margin_limit: z.number(),
  short_buy: z.number(),
  short_sell: z.number(),
  short_cash_repay: z.number(),
  short_balance_prev: z.number(),
  short_balance: z.number(),
  short_limit: z.number(),
  offset: z.number(),
});
export const MarginTradingListSchema = z.array(MarginTradingSchema);

// --- BrokerTrading ---
export const BrokerTradingSchema = z.object({
  date: z.string(),
  stock_id: z.string(),
  broker_id: z.string(),
  broker_name: z.string(),
  price: z.number(),
  buy_volume: z.number(),
  sell_volume: z.number(),
});
export const BrokerTradingListSchema = z.array(BrokerTradingSchema);

// --- Token ---
export const TokenResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
});

// --- Strategy ---
export const StrategySchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string().nullable(),
  strategy_type: z.string(),
  is_builtin: z.boolean(),
  params: z.record(z.string(), z.unknown()).nullable(),
});
export const StrategyListSchema = z.array(StrategySchema);

// --- Backtest ---
export const BacktestTradeSchema = z.object({
  id: z.number(),
  trade_date: z.string(),
  stock_id: z.string(),
  direction: z.enum(["buy", "sell"]),
  price: z.number(),
  quantity: z.number(),
  commission: z.number(),
  tax: z.number(),
  realized_pnl: z.number().nullable(),
});

export const BacktestDailyReturnSchema = z.object({
  date: z.string(),
  position_value: z.number(),
  cash: z.number(),
  total_equity: z.number(),
  daily_return: z.number().nullable(),
});

export const BacktestResultSchema = z.object({
  total_return: z.number(),
  annualized_return: z.number(),
  max_drawdown: z.number(),
  sharpe_ratio: z.number(),
  win_rate: z.number(),
  profit_loss_ratio: z.number(),
  total_trades: z.number(),
  avg_holding_days: z.number(),
  final_equity: z.number(),
});

export const BacktestSchema = z.object({
  id: z.number(),
  strategy_id: z.number(),
  stock_id: z.string(),
  start_date: z.string(),
  end_date: z.string(),
  initial_capital: z.number(),
  status: z.enum(["pending", "running", "completed", "failed"]),
  error_message: z.string().nullable(),
  result: BacktestResultSchema.nullable(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
  trades: z.array(BacktestTradeSchema).optional(),
  daily_returns: z.array(BacktestDailyReturnSchema).optional(),
});
export const BacktestListSchema = z.array(BacktestSchema);

// --- Safe parse helper ---
export function safeParse<T>(schema: z.ZodType<T>, data: unknown): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    console.warn("API response validation failed:", result.error.issues);
    return data as T; // fallback: 驗證失敗時仍回傳原始資料，不中斷功能
  }
  return result.data;
}
