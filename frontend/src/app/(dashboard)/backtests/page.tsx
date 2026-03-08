"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { safeParse, BacktestListSchema, StrategyListSchema } from "@/lib/schemas";
import { Button } from "@/components/ui/button";
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
import { LineChart, Plus } from "lucide-react";
import Pagination from "@/components/Pagination";
import BacktestListSkeleton from "@/components/skeletons/BacktestListSkeleton";
import type { Backtest, Strategy } from "@/types";

const PAGE_SIZE = 20;

const STATUS_MAP: Record<
  Backtest["status"],
  { label: string; variant: "secondary" | "default" | "destructive" | "outline" }
> = {
  pending: { label: "等待中", variant: "secondary" },
  running: { label: "執行中", variant: "default" },
  completed: { label: "已完成", variant: "outline" },
  failed: { label: "失敗", variant: "destructive" },
};

export default function BacktestsPage() {
  const router = useRouter();
  const [backtests, setBacktests] = useState<Backtest[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  useEffect(() => {
    setLoading(true);
    setError("");

    Promise.all([
      api.get("/api/backtests/", {
        params: { skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE },
      }),
      api.get("/api/backtests/strategies/"),
    ])
      .then(([btRes, stRes]) => {
        setBacktests(safeParse(BacktestListSchema, btRes.data));
        setStrategies(safeParse(StrategyListSchema, stRes.data));
        const total = Number(btRes.headers["x-total-count"] ?? 0);
        setTotalCount(total);
      })
      .catch(() => setError("載入回測資料失敗"))
      .finally(() => setLoading(false));
  }, [page]);

  const getStrategyName = (strategyId: number) => {
    const s = strategies.find((st) => st.id === strategyId);
    return s?.name ?? `策略 #${strategyId}`;
  };

  if (loading) {
    return <BacktestListSkeleton />;
  }

  if (error) {
    return <p className="text-destructive text-center mt-10">{error}</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">回測列表</h1>
          <p className="text-sm text-muted-foreground mt-1">
            管理並檢視所有策略回測結果
          </p>
        </div>
        <Button onClick={() => router.push("/backtests/new")}>
          <Plus className="h-4 w-4 mr-1.5" />
          新增回測
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {backtests.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <LineChart className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <p className="text-lg font-medium text-muted-foreground mb-1">
                尚無回測記錄
              </p>
              <p className="text-sm text-muted-foreground/70">
                點擊右上角「新增回測」按鈕來建立您的第一筆回測
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>策略名稱</TableHead>
                  <TableHead>股票</TableHead>
                  <TableHead>日期區間</TableHead>
                  <TableHead>狀態</TableHead>
                  <TableHead className="text-right">總報酬率</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {backtests.map((bt) => {
                  const status = STATUS_MAP[bt.status];
                  return (
                    <TableRow
                      key={bt.id}
                      className="cursor-pointer hover:bg-muted/50 even:bg-muted/30"
                      onClick={() => router.push(`/backtests/${bt.id}`)}
                    >
                      <TableCell className="font-semibold">
                        {getStrategyName(bt.strategy_id)}
                      </TableCell>
                      <TableCell className="font-mono">{bt.stock_id}</TableCell>
                      <TableCell>
                        {bt.start_date} ~ {bt.end_date}
                      </TableCell>
                      <TableCell>
                        <Badge variant={status.variant}>{status.label}</Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {bt.result
                          ? `${(bt.result.total_return * 100).toFixed(2)}%`
                          : "-"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
