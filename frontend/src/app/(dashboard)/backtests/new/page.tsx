"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { safeParse, StrategyListSchema } from "@/lib/schemas";
import { useDebounce } from "@/hooks/useDebounce";
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
import { Plus, X } from "lucide-react";

type BacktestMode = "single" | "batch" | "portfolio";

interface StockSuggestion {
  stock_id: string;
  stock_name: string;
}

function StockAutocomplete({
  value,
  onChange,
  placeholder,
  id,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  id?: string;
}) {
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const debouncedValue = useDebounce(value, 300);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debouncedValue.length < 2) {
      setSuggestions([]);
      return;
    }
    api
      .get("/api/stocks/", { params: { q: debouncedValue, limit: 5 } })
      .then((res) => {
        setSuggestions(res.data);
        setShowSuggestions(true);
      })
      .catch(() => setSuggestions([]));
  }, [debouncedValue]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <Input
        id={id}
        placeholder={placeholder ?? "例如: 2330"}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setShowSuggestions(true);
        }}
        onFocus={() => {
          if (suggestions.length > 0) setShowSuggestions(true);
        }}
        autoComplete="off"
      />
      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-md">
          {suggestions.map((s) => (
            <button
              key={s.stock_id}
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent text-left"
              onClick={() => {
                onChange(s.stock_id);
                setShowSuggestions(false);
                setSuggestions([]);
              }}
            >
              <span className="font-mono">{s.stock_id}</span>
              <span className="text-muted-foreground">{s.stock_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

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

  // Advanced mode state
  const [isAdvanced, setIsAdvanced] = useState(false);
  const [mode, setMode] = useState<BacktestMode>("single");
  const [stockIds, setStockIds] = useState<string[]>([""]);

  // Risk params
  const [stopLossPct, setStopLossPct] = useState("");
  const [takeProfitPct, setTakeProfitPct] = useState("");
  const [trailingStopPct, setTrailingStopPct] = useState("");
  const [positionSizePct, setPositionSizePct] = useState("100");

  // Scale-in
  const [allowScaleIn, setAllowScaleIn] = useState(false);
  const [maxScaleInTimes, setMaxScaleInTimes] = useState(3);

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

  const addStock = () => {
    if (stockIds.length >= 20) {
      toast.error("最多支援 20 檔股票");
      return;
    }
    setStockIds([...stockIds, ""]);
  };

  const removeStock = (index: number) => {
    if (stockIds.length <= 1) return;
    setStockIds(stockIds.filter((_, i) => i !== index));
  };

  const updateStock = (index: number, value: string) => {
    const updated = [...stockIds];
    updated[index] = value;
    setStockIds(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate common fields
    if (!selectedStrategyId || !startDate || !endDate) {
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

    // Validate stock selection
    if (!isAdvanced || mode === "single") {
      if (!stockId) {
        setError("請填寫股票代碼");
        return;
      }
    } else {
      const validStocks = stockIds.filter((s) => s.trim());
      if (validStocks.length < 2) {
        setError("批次 / 投資組合模式至少需要 2 檔股票");
        return;
      }
    }

    setLoading(true);
    setError("");

    const parsedParams: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(strategyParams)) {
      const num = Number(value);
      parsedParams[key] = isNaN(num) ? value : num;
    }

    // Build request body
    const body: Record<string, unknown> = {
      strategy_id: Number(selectedStrategyId),
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      params: Object.keys(parsedParams).length > 0 ? parsedParams : undefined,
    };

    if (!isAdvanced) {
      // Simple mode: single, no risk_params
      body.mode = "single";
      body.stock_id = stockId;
    } else {
      body.mode = mode;
      if (mode === "single") {
        body.stock_id = stockId;
      } else {
        body.stock_ids = stockIds.filter((s) => s.trim());
      }

      // Build risk_params (only include non-null values)
      const riskParams: Record<string, unknown> = {};
      const sl = parseFloat(stopLossPct);
      const tp = parseFloat(takeProfitPct);
      const ts = parseFloat(trailingStopPct);
      const ps = parseFloat(positionSizePct);

      if (!isNaN(sl) && sl > 0) riskParams.stop_loss_pct = sl;
      if (!isNaN(tp) && tp > 0) riskParams.take_profit_pct = tp;
      if (!isNaN(ts) && ts > 0) riskParams.trailing_stop_pct = ts;
      if (!isNaN(ps) && ps > 0) riskParams.position_size_pct = ps;
      else riskParams.position_size_pct = 100;

      riskParams.allow_scale_in = allowScaleIn;
      if (allowScaleIn) {
        riskParams.max_scale_in_times = maxScaleInTimes;
      } else {
        riskParams.max_scale_in_times = 0;
      }

      if (Object.keys(riskParams).length > 0) {
        body.risk_params = riskParams;
      }
    }

    try {
      await api.post("/api/backtests/", body);
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

            {/* Advanced: Mode Selection */}
            {isAdvanced && (
              <div className="space-y-2">
                <Label className="text-sm font-medium">回測模式</Label>
                <Select
                  value={mode}
                  onValueChange={(v) => setMode(v as BacktestMode)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="single">個股</SelectItem>
                    <SelectItem value="batch">批次比較</SelectItem>
                    <SelectItem value="portfolio">投資組合</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Stock ID - single mode */}
            {(!isAdvanced || mode === "single") && (
              <div className="space-y-2">
                <Label htmlFor="stockId" className="text-sm font-medium">股票代碼</Label>
                {isAdvanced ? (
                  <StockAutocomplete
                    id="stockId"
                    value={stockId}
                    onChange={setStockId}
                  />
                ) : (
                  <Input
                    id="stockId"
                    placeholder="例如: 2330"
                    value={stockId}
                    onChange={(e) => setStockId(e.target.value)}
                  />
                )}
              </div>
            )}

            {/* Multi-stock input - batch/portfolio mode */}
            {isAdvanced && (mode === "batch" || mode === "portfolio") && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium">
                    股票清單
                    <span className="text-muted-foreground font-normal ml-1">
                      ({stockIds.length}/20)
                    </span>
                  </Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addStock}
                    disabled={stockIds.length >= 20}
                    className="gap-1"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    新增股票
                  </Button>
                </div>
                <div className="space-y-2">
                  {stockIds.map((sid, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <StockAutocomplete
                        value={sid}
                        onChange={(v) => updateStock(index, v)}
                        placeholder={`股票 ${index + 1}`}
                      />
                      {stockIds.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeStock(index)}
                          className="shrink-0 text-muted-foreground hover:text-destructive"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

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

            {/* Advanced: Risk Params */}
            {isAdvanced && (
              <div className="space-y-4 rounded-lg border border-border bg-muted/30 p-4">
                <Label className="text-sm font-semibold">風控設定</Label>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="stopLoss" className="text-sm text-muted-foreground">停損 %</Label>
                    <Input
                      id="stopLoss"
                      type="number"
                      step="0.1"
                      min="0"
                      placeholder="不設定"
                      value={stopLossPct}
                      onChange={(e) => setStopLossPct(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="takeProfit" className="text-sm text-muted-foreground">停利 %</Label>
                    <Input
                      id="takeProfit"
                      type="number"
                      step="0.1"
                      min="0"
                      placeholder="不設定"
                      value={takeProfitPct}
                      onChange={(e) => setTakeProfitPct(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="trailingStop" className="text-sm text-muted-foreground">移動停損 %</Label>
                    <Input
                      id="trailingStop"
                      type="number"
                      step="0.1"
                      min="0"
                      placeholder="不設定"
                      value={trailingStopPct}
                      onChange={(e) => setTrailingStopPct(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="positionSize" className="text-sm text-muted-foreground">每次下單比例 %</Label>
                    <Input
                      id="positionSize"
                      type="number"
                      step="1"
                      min="1"
                      max="100"
                      value={positionSizePct}
                      onChange={(e) => setPositionSizePct(e.target.value)}
                    />
                  </div>
                </div>

                {/* Scale-in */}
                <div className="space-y-3 pt-2 border-t border-border">
                  <div className="flex items-center gap-3">
                    <input
                      id="allowScaleIn"
                      type="checkbox"
                      checked={allowScaleIn}
                      onChange={(e) => setAllowScaleIn(e.target.checked)}
                      className="h-4 w-4 rounded border-border"
                    />
                    <Label htmlFor="allowScaleIn" className="text-sm text-muted-foreground cursor-pointer">
                      允許加碼
                    </Label>
                  </div>
                  {allowScaleIn && (
                    <div className="space-y-2 pl-7">
                      <Label htmlFor="maxScaleIn" className="text-sm text-muted-foreground">最大加碼次數</Label>
                      <Input
                        id="maxScaleIn"
                        type="number"
                        min="1"
                        max="10"
                        value={maxScaleInTimes}
                        onChange={(e) => setMaxScaleInTimes(Number(e.target.value))}
                        className="w-32"
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {error && <p className="text-destructive text-sm">{error}</p>}

            <div className="flex items-center gap-3 pt-2">
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
              <div className="flex-1" />
              <button
                type="button"
                className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-4 transition-colors"
                onClick={() => setIsAdvanced(!isAdvanced)}
              >
                {isAdvanced ? "切換簡易模式" : "切換進階模式"}
              </button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
