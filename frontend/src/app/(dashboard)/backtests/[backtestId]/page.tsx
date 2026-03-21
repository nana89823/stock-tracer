"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import { safeParse, BacktestSchema, StrategyListSchema } from "@/lib/schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TrendingUp, TrendingDown, Target, BarChart3, Award, Repeat } from "lucide-react";
import EquityCurveChart from "@/components/charts/EquityCurveChart";
import BacktestDetailSkeleton from "@/components/skeletons/BacktestDetailSkeleton";
import type { Backtest, Strategy } from "@/types";
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

function formatCurrency(value: number): string {
  return value.toLocaleString("zh-TW", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold">回測 #{backtest.id}</h1>
              <Badge variant={status.variant} className="text-xs">{status.label}</Badge>
            </div>
            <p className="text-lg text-muted-foreground">
              {strategy?.name ?? `策略 #${backtest.strategy_id}`}
              <span className="mx-2 text-border">|</span>
              <span className="font-mono">{backtest.stock_id}</span>
            </p>
          </div>
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
              <p className="text-amber-600 text-center">
                回測執行時間過長，請稍後手動重新整理
              </p>
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
          {/* Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <Card className="relative overflow-hidden">
              <div className={`absolute inset-y-0 left-0 w-1 ${backtest.result.total_return >= 0 ? "bg-green-500" : "bg-red-500"}`} />
              <CardHeader className="pb-2 pl-5">
                <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  <TrendingUp className="h-3.5 w-3.5" />
                  總報酬率
                </CardTitle>
              </CardHeader>
              <CardContent className="pl-5">
                <p
                  className={`text-2xl font-bold ${
                    backtest.result.total_return >= 0
                      ? "text-stock-up"
                      : "text-stock-down"
                  }`}
                >
                  {formatPercent(backtest.result.total_return)}
                </p>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden">
              <div className={`absolute inset-y-0 left-0 w-1 ${backtest.result.annualized_return >= 0 ? "bg-green-500" : "bg-red-500"}`} />
              <CardHeader className="pb-2 pl-5">
                <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  <BarChart3 className="h-3.5 w-3.5" />
                  年化報酬率
                </CardTitle>
              </CardHeader>
              <CardContent className="pl-5">
                <p
                  className={`text-2xl font-bold ${
                    backtest.result.annualized_return >= 0
                      ? "text-stock-up"
                      : "text-stock-down"
                  }`}
                >
                  {formatPercent(backtest.result.annualized_return)}
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
                  {formatPercent(backtest.result.max_drawdown)}
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
                  {backtest.result.sharpe_ratio.toFixed(2)}
                </p>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden">
              <div className={`absolute inset-y-0 left-0 w-1 ${backtest.result.win_rate > 0.5 ? "bg-green-500" : "bg-amber-500"}`} />
              <CardHeader className="pb-2 pl-5">
                <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  <Target className="h-3.5 w-3.5" />
                  勝率
                </CardTitle>
              </CardHeader>
              <CardContent className="pl-5">
                <p className={`text-2xl font-bold ${backtest.result.win_rate > 0.5 ? "text-stock-up" : ""}`}>
                  {formatPercent(backtest.result.win_rate)}
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
                  {backtest.result.total_trades}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Equity Curve */}
          <Card>
            <CardHeader>
              <CardTitle>權益曲線</CardTitle>
            </CardHeader>
            <CardContent>
              {backtest.daily_returns && backtest.daily_returns.length > 0 ? (
                <EquityCurveChart data={backtest.daily_returns} />
              ) : (
                <p className="text-muted-foreground text-center py-10">
                  無每日報酬資料
                </p>
              )}
            </CardContent>
          </Card>

          {/* Trades Table */}
          <Card>
            <CardHeader>
              <CardTitle>交易記錄</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {backtest.trades && backtest.trades.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>日期</TableHead>
                      <TableHead>方向</TableHead>
                      <TableHead className="text-right">價格</TableHead>
                      <TableHead className="text-right">數量</TableHead>
                      <TableHead className="text-right">手續費</TableHead>
                      <TableHead className="text-right">稅</TableHead>
                      <TableHead className="text-right">損益</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {backtest.trades.map((trade) => (
                      <TableRow key={trade.id}>
                        <TableCell>{trade.trade_date}</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              trade.direction === "buy"
                                ? "default"
                                : "destructive"
                            }
                          >
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
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-muted-foreground text-center py-10">
                  無交易記錄
                </p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
