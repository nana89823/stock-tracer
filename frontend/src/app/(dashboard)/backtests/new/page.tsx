"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { safeParse, StrategyListSchema } from "@/lib/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Strategy } from "@/types";
import { toast } from "sonner";

export default function NewBacktestPage() {
  const router = useRouter();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState("");
  const [stockId, setStockId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [initialCapital, setInitialCapital] = useState(1000000);
  const [strategyParams, setStrategyParams] = useState<Record<string, string>>(
    {}
  );
  const [loading, setLoading] = useState(false);
  const [fetchingStrategies, setFetchingStrategies] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/backtests/strategies/")
      .then((res) => setStrategies(safeParse(StrategyListSchema, res.data)))
      .catch(() => setError("載入策略失敗"))
      .finally(() => setFetchingStrategies(false));
  }, []);

  const selectedStrategy = strategies.find(
    (s) => s.id === Number(selectedStrategyId)
  );

  useEffect(() => {
    if (selectedStrategy?.params) {
      const defaults: Record<string, string> = {};
      for (const [key, value] of Object.entries(selectedStrategy.params)) {
        defaults[key] = String(value ?? "");
      }
      setStrategyParams(defaults);
    } else {
      setStrategyParams({});
    }
  }, [selectedStrategyId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStrategyId || !stockId || !startDate || !endDate) {
      setError("請填寫所有必填欄位");
      return;
    }

    if (endDate <= startDate) {
      toast.error("結束日期必須大於開始日期");
      return;
    }

    if (initialCapital <= 0) {
      toast.error("初始資金必須大於 0");
      return;
    }

    setLoading(true);
    setError("");

    const parsedParams: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(strategyParams)) {
      const num = Number(value);
      parsedParams[key] = isNaN(num) ? value : num;
    }

    try {
      await api.post("/api/backtests/", {
        strategy_id: Number(selectedStrategyId),
        stock_id: stockId,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        params: Object.keys(parsedParams).length > 0 ? parsedParams : undefined,
      });
      router.push("/backtests");
    } catch {
      setError("建立回測失敗，請稍後再試");
    } finally {
      setLoading(false);
    }
  };

  if (fetchingStrategies) {
    return <p className="text-muted-foreground text-center mt-10">載入中...</p>;
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">新增回測</h1>
        <p className="text-sm text-muted-foreground mt-1">
          選擇策略與參數，設定回測區間來驗證交易策略的績效表現
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>回測設定</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Strategy */}
            <div className="space-y-2">
              <Label htmlFor="strategy" className="text-sm font-medium">策略</Label>
              <Select
                value={selectedStrategyId}
                onValueChange={(v) => setSelectedStrategyId(v ?? "")}
              >
                <SelectTrigger id="strategy">
                  {selectedStrategy
                    ? `${selectedStrategy.name}${selectedStrategy.description ? ` - ${selectedStrategy.description}` : ""}`
                    : <SelectValue placeholder="選擇策略" />}
                </SelectTrigger>
                <SelectContent>
                  {strategies.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.name}
                      {s.description ? ` - ${s.description}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Stock ID */}
            <div className="space-y-2">
              <Label htmlFor="stockId" className="text-sm font-medium">股票代碼</Label>
              <Input
                id="stockId"
                placeholder="例如: 2330"
                value={stockId}
                onChange={(e) => setStockId(e.target.value)}
              />
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="startDate" className="text-sm font-medium">開始日期</Label>
                <Input
                  id="startDate"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="endDate" className="text-sm font-medium">結束日期</Label>
                <Input
                  id="endDate"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>

            {/* Initial Capital */}
            <div className="space-y-2">
              <Label htmlFor="capital" className="text-sm font-medium">初始資金</Label>
              <Input
                id="capital"
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(Number(e.target.value))}
              />
            </div>

            {/* Dynamic Strategy Params */}
            {selectedStrategy?.params &&
              Object.keys(selectedStrategy.params).length > 0 && (
                <div className="space-y-4 rounded-lg border border-border bg-muted/30 p-4">
                  <Label className="text-sm font-semibold">策略參數</Label>
                  <div className="grid grid-cols-2 gap-4">
                    {Object.entries(selectedStrategy.params).map(
                      ([key]) => (
                        <div key={key} className="space-y-2">
                          <Label htmlFor={`param-${key}`} className="text-sm text-muted-foreground">{key}</Label>
                          <Input
                            id={`param-${key}`}
                            value={strategyParams[key] ?? ""}
                            onChange={(e) =>
                              setStrategyParams((prev) => ({
                                ...prev,
                                [key]: e.target.value,
                              }))
                            }
                          />
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

            {error && <p className="text-destructive text-sm">{error}</p>}

            <div className="flex gap-3 pt-2">
              <Button type="submit" disabled={loading} className="min-w-[120px]">
                {loading ? "建立中..." : "建立回測"}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="min-w-[80px]"
                onClick={() => router.push("/backtests")}
              >
                取消
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
