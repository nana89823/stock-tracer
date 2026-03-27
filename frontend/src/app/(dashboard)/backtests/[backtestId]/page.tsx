"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import { safeParse, BacktestSchema, StrategyListSchema } from "@/lib/schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  TrendingUp,
  TrendingDown,
  Target,
  BarChart3,
  Award,
  Repeat,
  RefreshCw,
  Download,
  Shield,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import EquityCurveChart from "@/components/charts/EquityCurveChart";
import BacktestDetailSkeleton from "@/components/skeletons/BacktestDetailSkeleton";
import type { Backtest, Strategy, BacktestResult, BacktestTrade, BacktestDailyReturn } from "@/types";
import { toast } from "sonner";

const STATUS_MAP: Record<
  Backtest["status"],
  { label: string; variant: "secondary" | "default" | "destructive" | "outline" }
> = {
  pending: { label: "等待中", variant: "secondary" },
  running: { label: "執行中", variant: "default" },
  completed: { label: "已完成", variant: "outline" },
  failed: { label: "失敗", variant: "destructive" },
};

const REASON_MAP: Record<string, string> = {
  strategy: "策略",
  stop_loss: "停損",
  take_profit: "停利",
  trailing_stop: "移動停損",
};

const MODE_MAP: Record<string, string> = {
  single: "個股",
  batch: "批次比較",
  portfolio: "投資組合",
};

const STOCK_COLORS = [
  "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#06b6d4",
  "#84cc16", "#e11d48", "#0ea5e9", "#a855f7", "#10b981",
  "#d946ef", "#facc15", "#4ade80", "#fb923c", "#818cf8",
];

function formatCurrency(value: number): string {
  return value.toLocaleString("zh-TW", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

// --- Metric Cards ---
function MetricCards({ result }: { result: BacktestResult }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      <Card className="relative overflow-hidden">
        <div className={`absolute inset-y-0 left-0 w-1 ${result.total_return >= 0 ? "bg-green-500" : "bg-red-500"}`} />
        <CardHeader className="pb-2 pl-5">
          <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <TrendingUp className="h-3.5 w-3.5" />
            總報酬率
          </CardTitle>
        </CardHeader>
        <CardContent className="pl-5">
          <p className={`text-2xl font-bold ${result.total_return >= 0 ? "text-stock-up" : "text-stock-down"}`}>
            {formatPercent(result.total_return)}
          </p>
        </CardContent>
      </Card>

      <Card className="relative overflow-hidden">
        <div className={`absolute inset-y-0 left-0 w-1 ${result.annualized_return >= 0 ? "bg-green-500" : "bg-red-500"}`} />
        <CardHeader className="pb-2 pl-5">
          <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <BarChart3 className="h-3.5 w-3.5" />
            年化報酬率
          </CardTitle>
        </CardHeader>
        <CardContent className="pl-5">
          <p className={`text-2xl font-bold ${result.annualized_return >= 0 ? "text-stock-up" : "text-stock-down"}`}>
            {formatPercent(result.annualized_return)}
          </p>
        </CardContent>
      </Card>

      <Card className="relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 w-1 bg-red-500" />
        <CardHeader className="pb-2 pl-5">
          <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <TrendingDown className="h-3.5 w-3.5" />
            最大回撤
          </CardTitle>
        </CardHeader>
        <CardContent className="pl-5">
          <p className="text-2xl font-bold text-stock-down">
            {formatPercent(result.max_drawdown)}
          </p>
        </CardContent>
      </Card>

      <Card className="relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 w-1 bg-blue-500" />
        <CardHeader className="pb-2 pl-5">
          <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <Award className="h-3.5 w-3.5" />
            夏普比率
          </CardTitle>
        </CardHeader>
        <CardContent className="pl-5">
          <p className="text-2xl font-bold">
            {result.sharpe_ratio.toFixed(2)}
          </p>
        </CardContent>
      </Card>

      <Card className="relative overflow-hidden">
        <div className={`absolute inset-y-0 left-0 w-1 ${result.win_rate > 0.5 ? "bg-green-500" : "bg-amber-500"}`} />
        <CardHeader className="pb-2 pl-5">
          <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <Target className="h-3.5 w-3.5" />
            勝率
          </CardTitle>
        </CardHeader>
        <CardContent className="pl-5">
          <p className={`text-2xl font-bold ${result.win_rate > 0.5 ? "text-stock-up" : ""}`}>
            {formatPercent(result.win_rate)}
          </p>
        </CardContent>
      </Card>

      <Card className="relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 w-1 bg-blue-500" />
        <CardHeader className="pb-2 pl-5">
          <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
            <Repeat className="h-3.5 w-3.5" />
            交易次數
          </CardTitle>
        </CardHeader>
        <CardContent className="pl-5">
          <p className="text-2xl font-bold">
            {result.total_trades}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// --- Risk Params Card ---
function RiskParamsCard({ backtest }: { backtest: Backtest }) {
  const rp = backtest.risk_params;
  if (!rp) return null;

  const hasAnyRisk = rp.stop_loss_pct !== null || rp.take_profit_pct !== null || rp.trailing_stop_pct !== null || rp.position_size_pct !== 100 || rp.allow_scale_in;
  if (!hasAnyRisk) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-1.5 text-sm">
          <Shield className="h-4 w-4" />
          風控設定
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-2 text-sm">
          {rp.stop_loss_pct !== null && (
            <div>
              <span className="text-muted-foreground">停損:</span>{" "}
              <span className="font-mono">{rp.stop_loss_pct}%</span>
            </div>
          )}
          {rp.take_profit_pct !== null && (
            <div>
              <span className="text-muted-foreground">停利:</span>{" "}
              <span className="font-mono">{rp.take_profit_pct}%</span>
            </div>
          )}
          {rp.trailing_stop_pct !== null && (
            <div>
              <span className="text-muted-foreground">移動停損:</span>{" "}
              <span className="font-mono">{rp.trailing_stop_pct}%</span>
            </div>
          )}
          {rp.position_size_pct !== 100 && (
            <div>
              <span className="text-muted-foreground">下單比例:</span>{" "}
              <span className="font-mono">{rp.position_size_pct}%</span>
            </div>
          )}
          {rp.allow_scale_in && (
            <div>
              <span className="text-muted-foreground">加碼:</span>{" "}
              <span className="font-mono">最多 {rp.max_scale_in_times} 次</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// --- Trades Table ---
function TradesTable({
  trades,
  showStockId = false,
  showReason = false,
}: {
  trades: BacktestTrade[];
  showStockId?: boolean;
  showReason?: boolean;
}) {
  if (!trades || trades.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-10">
        無交易記錄
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>日期</TableHead>
          {showStockId && <TableHead>股票</TableHead>}
          <TableHead>方向</TableHead>
          <TableHead className="text-right">價格</TableHead>
          <TableHead className="text-right">數量</TableHead>
          <TableHead className="text-right">手續費</TableHead>
          <TableHead className="text-right">稅</TableHead>
          <TableHead className="text-right">損益</TableHead>
          {showReason && <TableHead>原因</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {trades.map((trade) => (
          <TableRow key={trade.id}>
            <TableCell>{trade.trade_date}</TableCell>
            {showStockId && (
              <TableCell className="font-mono">{trade.stock_id}</TableCell>
            )}
            <TableCell>
              <Badge variant={trade.direction === "buy" ? "default" : "destructive"}>
                {trade.direction === "buy" ? "買" : "賣"}
              </Badge>
            </TableCell>
            <TableCell className="text-right font-mono">
              {trade.price.toLocaleString()}
            </TableCell>
            <TableCell className="text-right font-mono">
              {trade.quantity.toLocaleString()}
            </TableCell>
            <TableCell className="text-right font-mono">
              {trade.commission.toLocaleString()}
            </TableCell>
            <TableCell className="text-right font-mono">
              {trade.tax.toLocaleString()}
            </TableCell>
            <TableCell
              className={`text-right font-mono ${
                trade.realized_pnl !== null
                  ? trade.realized_pnl >= 0
                    ? "text-stock-up"
                    : "text-stock-down"
                  : ""
              }`}
            >
              {trade.realized_pnl !== null
                ? trade.realized_pnl.toLocaleString()
                : "-"}
            </TableCell>
            {showReason && (
              <TableCell className="text-muted-foreground">
                {REASON_MAP[trade.reason ?? "strategy"] ?? trade.reason ?? "-"}
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// --- Batch Comparison Chart ---
function BatchComparisonChart({
  dailyReturns,
  stockIds,
}: {
  dailyReturns: BacktestDailyReturn[];
  stockIds: string[];
}) {
  const chartData = useMemo(() => {
    // Group by date, create { date, [stock_id]: total_equity }
    const dateMap: Record<string, Record<string, number>> = {};
    for (const d of dailyReturns) {
      if (!d.stock_id) continue;
      if (!dateMap[d.date]) dateMap[d.date] = {};
      dateMap[d.date][d.stock_id] = d.total_equity;
    }
    return Object.entries(dateMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, values]) => ({ date, ...values }));
  }, [dailyReturns]);

  if (chartData.length === 0) {
    return <p className="text-muted-foreground text-center py-10">無比較資料</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => v.toLocaleString()} />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1a1a2e",
            border: "1px solid #333",
            borderRadius: "8px",
          }}
          formatter={(value, name) => [
            `$${Number(value).toLocaleString()}`,
            String(name),
          ]}
          labelFormatter={(label) => `日期: ${label}`}
        />
        <Legend />
        {stockIds.map((sid, i) => (
          <Line
            key={sid}
            type="monotone"
            dataKey={sid}
            stroke={STOCK_COLORS[i % STOCK_COLORS.length]}
            dot={false}
            strokeWidth={2}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

// --- Single Mode Detail ---
function SingleModeDetail({ backtest }: { backtest: Backtest }) {
  const hasRiskParams = !!backtest.risk_params;
  const showReason = hasRiskParams || backtest.trades?.some((t) => t.reason && t.reason !== "strategy");

  return (
    <>
      <RiskParamsCard backtest={backtest} />
      <MetricCards result={backtest.result!} />

      <Card>
        <CardHeader>
          <CardTitle>權益曲線</CardTitle>
        </CardHeader>
        <CardContent>
          {backtest.daily_returns && backtest.daily_returns.length > 0 ? (
            <EquityCurveChart data={backtest.daily_returns} />
          ) : (
            <p className="text-muted-foreground text-center py-10">無每日報酬資料</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>交易記錄</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <TradesTable trades={backtest.trades ?? []} showReason={!!showReason} />
        </CardContent>
      </Card>
    </>
  );
}

// --- Batch Mode Detail ---
function BatchModeDetail({ backtest }: { backtest: Backtest }) {
  const stockIds = backtest.stock_ids ?? [];
  const [activeTab, setActiveTab] = useState(stockIds[0] ?? "");
  const perStockResults = backtest.per_stock_results ?? [];

  // Summary stats
  const avgReturn = perStockResults.length > 0
    ? perStockResults.reduce((acc, r) => acc + r.metrics.total_return, 0) / perStockResults.length
    : 0;
  const bestStock = perStockResults.length > 0
    ? perStockResults.reduce((best, r) => r.metrics.total_return > best.metrics.total_return ? r : best)
    : null;
  const worstStock = perStockResults.length > 0
    ? perStockResults.reduce((worst, r) => r.metrics.total_return < worst.metrics.total_return ? r : worst)
    : null;

  const activeResult = perStockResults.find((r) => r.stock_id === activeTab);
  const activeTrades = (backtest.trades ?? []).filter((t) => t.stock_id === activeTab);
  const activeDailyReturns = (backtest.daily_returns ?? []).filter((d) => d.stock_id === activeTab);

  return (
    <>
      <RiskParamsCard backtest={backtest} />

      {/* Summary Card */}
      {perStockResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>批次比較摘要</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-6 text-sm">
              <div>
                <span className="text-muted-foreground">平均報酬率:</span>{" "}
                <span className={`font-bold font-mono ${avgReturn >= 0 ? "text-stock-up" : "text-stock-down"}`}>
                  {formatPercent(avgReturn)}
                </span>
              </div>
              {bestStock && (
                <div>
                  <span className="text-muted-foreground">最佳:</span>{" "}
                  <span className="font-mono">{bestStock.stock_id}</span>{" "}
                  <span className="text-stock-up font-mono">
                    {formatPercent(bestStock.metrics.total_return)}
                  </span>
                </div>
              )}
              {worstStock && (
                <div>
                  <span className="text-muted-foreground">最差:</span>{" "}
                  <span className="font-mono">{worstStock.stock_id}</span>{" "}
                  <span className="text-stock-down font-mono">
                    {formatPercent(worstStock.metrics.total_return)}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Comparison Chart */}
      <Card>
        <CardHeader>
          <CardTitle>權益曲線比較</CardTitle>
        </CardHeader>
        <CardContent>
          <BatchComparisonChart
            dailyReturns={backtest.daily_returns ?? []}
            stockIds={stockIds}
          />
        </CardContent>
      </Card>

      {/* Per-stock Tabs */}
      {stockIds.length > 0 && (
        <div className="space-y-4">
          <div className="flex gap-1 border-b border-border overflow-x-auto">
            {stockIds.map((sid) => (
              <button
                key={sid}
                type="button"
                onClick={() => setActiveTab(sid)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === sid
                    ? "border-primary text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                {sid}
              </button>
            ))}
          </div>

          {activeResult && <MetricCards result={activeResult.metrics} />}

          <Card>
            <CardHeader>
              <CardTitle>{activeTab} 權益曲線</CardTitle>
            </CardHeader>
            <CardContent>
              {activeDailyReturns.length > 0 ? (
                <EquityCurveChart data={activeDailyReturns} />
              ) : (
                <p className="text-muted-foreground text-center py-10">無每日報酬資料</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{activeTab} 交易記錄</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <TradesTable trades={activeTrades} showReason />
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}

// --- Portfolio Mode Detail ---
function PortfolioModeDetail({ backtest }: { backtest: Backtest }) {
  const stockIds = backtest.stock_ids ?? [];
  const portfolioDailyReturns = (backtest.daily_returns ?? []).filter((d) => !d.stock_id);

  return (
    <>
      <RiskParamsCard backtest={backtest} />

      {/* Portfolio Metrics */}
      {backtest.result && <MetricCards result={backtest.result} />}

      {/* Allocation Display */}
      {stockIds.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>配置比例 (等權重)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {stockIds.map((sid, i) => (
                <div
                  key={sid}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-muted/30"
                >
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: STOCK_COLORS[i % STOCK_COLORS.length] }}
                  />
                  <span className="font-mono text-sm">{sid}</span>
                  <span className="text-xs text-muted-foreground">
                    {(100 / stockIds.length).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Combined Equity Curve */}
      <Card>
        <CardHeader>
          <CardTitle>投資組合權益曲線</CardTitle>
        </CardHeader>
        <CardContent>
          {portfolioDailyReturns.length > 0 ? (
            <EquityCurveChart data={portfolioDailyReturns} />
          ) : (
            <p className="text-muted-foreground text-center py-10">無每日報酬資料</p>
          )}
        </CardContent>
      </Card>

      {/* Per-stock Equity Comparison */}
      {stockIds.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>個股權益曲線比較</CardTitle>
          </CardHeader>
          <CardContent>
            <BatchComparisonChart
              dailyReturns={backtest.daily_returns ?? []}
              stockIds={stockIds}
            />
          </CardContent>
        </Card>
      )}

      {/* Trades Table */}
      <Card>
        <CardHeader>
          <CardTitle>交易記錄</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <TradesTable trades={backtest.trades ?? []} showStockId showReason />
        </CardContent>
      </Card>
    </>
  );
}

// --- Main Page ---
export default function BacktestDetailPage() {
  const params = useParams();
  const backtestId = params.backtestId as string;

  const [backtest, setBacktest] = useState<Backtest | null>(null);
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pollCount, setPollCount] = useState(0);
  const MAX_POLL_COUNT = 200;

  const fetchBacktest = useCallback(() => {
    return api
      .get(`/api/backtests/${backtestId}`)
      .then((res) => {
        const parsed = safeParse(BacktestSchema, res.data);
        setBacktest(parsed);
        return parsed;
      })
      .catch(() => {
        setError("載入回測資料失敗");
        toast.error("載入回測資料失敗");
        return null;
      });
  }, [backtestId]);

  useEffect(() => {
    if (!backtestId) return;

    setLoading(true);
    setError("");

    fetchBacktest()
      .then((bt) => {
        if (bt) {
          return api
            .get(`/api/backtests/strategies/`)
            .then((res) => {
              const strategies = safeParse(StrategyListSchema, res.data);
              const matched = strategies.find((s) => s.id === bt.strategy_id);
              if (matched) setStrategy(matched);
            })
            .catch(() => {
              toast.error("載入策略資訊失敗");
            });
        }
      })
      .finally(() => setLoading(false));
  }, [backtestId, fetchBacktest]);

  // Polling for pending/running
  useEffect(() => {
    if (!backtest) return;
    if (backtest.status !== "pending" && backtest.status !== "running") return;
    if (pollCount >= MAX_POLL_COUNT) return;

    const interval = setInterval(() => {
      setPollCount((prev) => {
        const next = prev + 1;
        if (next >= MAX_POLL_COUNT) {
          clearInterval(interval);
          return next;
        }
        return next;
      });
      fetchBacktest();
    }, 3000);

    return () => clearInterval(interval);
  }, [backtest?.status, fetchBacktest, pollCount]);

  if (loading) {
    return <BacktestDetailSkeleton />;
  }

  if (error || !backtest) {
    return (
      <p className="text-destructive text-center mt-10">
        {error || "找不到回測資料"}
      </p>
    );
  }

  const status = STATUS_MAP[backtest.status];
  const isPendingOrRunning =
    backtest.status === "pending" || backtest.status === "running";
  const mode = backtest.mode ?? "single";
  const displayStockId = mode === "single"
    ? backtest.stock_id
    : (backtest.stock_ids ?? []).join(", ");

  const handleExportCsv = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`/api/backtests/${backtestId}/export`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("匯出失敗");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `backtest_${backtestId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("CSV 匯出成功");
    } catch {
      toast.error("CSV 匯出失敗");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold">回測 #{backtest.id}</h1>
              <Badge variant={status.variant} className="text-xs">{status.label}</Badge>
              {mode !== "single" && (
                <Badge variant="secondary" className="text-xs">
                  {MODE_MAP[mode] ?? mode}
                </Badge>
              )}
            </div>
            <p className="text-lg text-muted-foreground">
              {strategy?.name ?? `策略 #${backtest.strategy_id}`}
              <span className="mx-2 text-border">|</span>
              <span className="font-mono">{displayStockId}</span>
            </p>
          </div>
          {backtest.status === "completed" && (
            <Button variant="outline" className="gap-2" onClick={handleExportCsv}>
              <Download className="h-4 w-4" />
              匯出 CSV
            </Button>
          )}
        </div>
        <div className="flex gap-6 mt-4 text-sm text-muted-foreground">
          <span>期間: {backtest.start_date} ~ {backtest.end_date}</span>
          <span>初始資金: ${formatCurrency(backtest.initial_capital)}</span>
        </div>
      </div>

      {/* Pending / Running */}
      {isPendingOrRunning && (
        <Card>
          <CardContent className="py-20">
            {pollCount >= MAX_POLL_COUNT ? (
              <div className="flex flex-col items-center gap-4">
                <p className="text-amber-600 text-center">
                  回測執行時間較長，系統仍在處理中
                </p>
                <p className="text-sm text-muted-foreground text-center">
                  請稍後重新整理頁面查看最新狀態
                </p>
                <Button
                  variant="outline"
                  className="gap-2"
                  onClick={() => {
                    setPollCount(0);
                    fetchBacktest();
                  }}
                >
                  <RefreshCw className="h-4 w-4" />
                  重新整理
                </Button>
              </div>
            ) : (
              <p className="text-muted-foreground text-center">
                回測{backtest.status === "pending" ? "等待執行" : "執行"}中，請稍候...
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Failed */}
      {backtest.status === "failed" && (
        <Card>
          <CardContent className="py-10">
            <p className="text-destructive text-center">
              回測失敗: {backtest.error_message || "未知錯誤"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Completed */}
      {backtest.status === "completed" && backtest.result && (
        <>
          {mode === "batch" ? (
            <BatchModeDetail backtest={backtest} />
          ) : mode === "portfolio" ? (
            <PortfolioModeDetail backtest={backtest} />
          ) : (
            <SingleModeDetail backtest={backtest} />
          )}
        </>
      )}
    </div>
  );
}
