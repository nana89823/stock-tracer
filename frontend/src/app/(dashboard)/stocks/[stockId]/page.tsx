"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import {
  safeParse,
  StockSchema,
  RawPriceListSchema,
  RawChipListSchema,
  MajorHolderListSchema,
  MarginTradingListSchema,
  BrokerTradingListSchema,
} from "@/lib/schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import CandlestickChart from "@/components/charts/CandlestickChart";
import ChipChart from "@/components/charts/ChipChart";
import HoldersChart from "@/components/charts/HoldersChart";
import MarginChart from "@/components/charts/MarginChart";
import BrokerChart from "@/components/charts/BrokerChart";
import StockDetailSkeleton from "@/components/skeletons/StockDetailSkeleton";
import WatchlistButton from "@/components/WatchlistButton";
import DateRangePicker from "@/components/DateRangePicker";
import type { Stock, RawPrice, RawChip, MajorHolder, MarginTrading, BrokerTrading } from "@/types";
import { toast } from "sonner";

const LEVEL_LABELS: Record<number, string> = {
  1: "1-999",
  2: "1,000-5,000",
  3: "5,001-10,000",
  4: "10,001-15,000",
  5: "15,001-20,000",
  6: "20,001-30,000",
  7: "30,001-40,000",
  8: "40,001-50,000",
  9: "50,001-100,000",
  10: "100,001-200,000",
  11: "200,001-400,000",
  12: "400,001-600,000",
  13: "600,001-800,000",
  14: "800,001-1,000,000",
  15: "1,000,001以上",
  16: "合計",
};

export default function StockDetailPage() {
  const params = useParams();
  const stockId = params.stockId as string;

  const [stock, setStock] = useState<Stock | null>(null);
  const [prices, setPrices] = useState<RawPrice[]>([]);
  const [chips, setChips] = useState<RawChip[]>([]);
  const [holders, setHolders] = useState<MajorHolder[]>([]);
  const [margin, setMargin] = useState<MarginTrading[]>([]);
  const [brokers, setBrokers] = useState<BrokerTrading[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const formatDate = (d: Date) => d.toISOString().split("T")[0];
  const [startDate, setStartDate] = useState(() =>
    formatDate(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000))
  );
  const [endDate, setEndDate] = useState(() => formatDate(new Date()));

  const handleDateChange = useCallback((start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
  }, []);

  useEffect(() => {
    if (!stockId) return;

    setLoading(true);
    setError("");

    Promise.all([
      api.get(`/api/stocks/${stockId}`),
      api.get(`/api/stocks/${stockId}/prices`, {
        params: { start_date: startDate, end_date: endDate },
      }),
      api.get(`/api/stocks/${stockId}/chips`, {
        params: { start_date: startDate, end_date: endDate },
      }),
      api.get(`/api/stocks/${stockId}/holders`),
      api.get(`/api/stocks/${stockId}/margin`, {
        params: { start_date: startDate, end_date: endDate },
      }).catch(() => {
        toast.error("載入融資融券資料失敗");
        return { data: [] };
      }),
      api.get(`/api/stocks/${stockId}/brokers`).catch(() => {
        toast.error("載入券商資料失敗");
        return { data: [] };
      }),
    ])
      .then(([stockRes, priceRes, chipRes, holderRes, marginRes, brokerRes]) => {
        setStock(safeParse(StockSchema, stockRes.data));
        setPrices(safeParse(RawPriceListSchema, priceRes.data));
        setChips(safeParse(RawChipListSchema, chipRes.data));
        setHolders(safeParse(MajorHolderListSchema, holderRes.data));
        setMargin(safeParse(MarginTradingListSchema, marginRes.data));
        setBrokers(safeParse(BrokerTradingListSchema, brokerRes.data));
      })
      .catch(() => {
        setError("載入資料失敗");
        toast.error("載入資料失敗");
      })
      .finally(() => setLoading(false));
  }, [stockId, startDate, endDate]);

  if (loading) {
    return <StockDetailSkeleton />;
  }

  if (error) {
    return <p className="text-destructive text-center mt-10">{error}</p>;
  }

  const latestPrice = prices.length > 0 ? prices[prices.length - 1] : null;
  const priceChange = latestPrice?.price_change ?? 0;
  const isUp = priceChange >= 0;

  return (
    <div className="space-y-6">
      {/* Stock Header */}
      <Card>
        <CardContent className="py-5">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-1">
                <h1 className="text-2xl font-bold">
                  {stock?.stock_name}
                </h1>
                <WatchlistButton stockId={stockId} />
              </div>
              <p className="text-muted-foreground text-sm mt-0.5">
                {stock?.stock_id} &middot; {stock?.market_type === "tpex" ? "上櫃" : "上市"}
              </p>
            </div>
            {latestPrice && (
              <div className="text-right">
                <span className={`text-3xl font-bold tracking-tight ${isUp ? "text-stock-up" : "text-stock-down"}`}>
                  {latestPrice.close_price.toFixed(2)}
                </span>
                <p className={`text-sm mt-0.5 ${isUp ? "text-stock-up" : "text-stock-down"}`}>
                  {isUp ? "+" : ""}
                  {priceChange.toFixed(2)}
                  {latestPrice.close_price - priceChange !== 0 && (
                    <span className="ml-1.5">
                      ({isUp ? "+" : ""}
                      {((priceChange / (latestPrice.close_price - priceChange)) * 100).toFixed(2)}%)
                    </span>
                  )}
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Date Range Picker */}
      <DateRangePicker
        startDate={startDate}
        endDate={endDate}
        onChange={handleDateChange}
      />

      {/* Candlestick Chart - Full width */}
      <Card>
        <CardHeader>
          <CardTitle>K 線圖</CardTitle>
        </CardHeader>
        <CardContent>
          {prices.length > 0 ? (
            <CandlestickChart data={prices} />
          ) : (
            <p className="text-muted-foreground text-center py-10">無價格資料</p>
          )}
        </CardContent>
      </Card>

      {/* Chip + Holders side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>三大法人買賣超</CardTitle>
          </CardHeader>
          <CardContent>
            {chips.length > 0 ? (
              <ChipChart data={chips} />
            ) : (
              <p className="text-muted-foreground text-center py-10">無籌碼資料</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>大戶持股分布</CardTitle>
          </CardHeader>
          <CardContent>
            {holders.length > 0 ? (
              <HoldersChart data={holders} />
            ) : (
              <p className="text-muted-foreground text-center py-10">無持股資料</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Margin + Broker side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>融資融券</CardTitle>
          </CardHeader>
          <CardContent>
            {margin.length > 0 ? (
              <MarginChart data={margin} />
            ) : (
              <p className="text-muted-foreground text-center py-10">無融資融券資料</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>分點券商進出 (Top 20)</CardTitle>
          </CardHeader>
          <CardContent>
            {brokers.length > 0 ? (
              <BrokerChart data={brokers} />
            ) : (
              <p className="text-muted-foreground text-center py-10">無分點券商資料</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Holders Table - Full width */}
      {holders.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>持股分布明細</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>持股/單位數分級</TableHead>
                  <TableHead className="text-right">人數</TableHead>
                  <TableHead className="text-right">張數</TableHead>
                  <TableHead className="text-right">占集保庫存數比例 (%)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {holders.map((h) => (
                  <TableRow
                    key={h.holding_level}
                    className={h.holding_level === 16 ? "font-bold bg-muted/30" : ""}
                  >
                    <TableCell>
                      {LEVEL_LABELS[h.holding_level] || `Level ${h.holding_level}`}
                    </TableCell>
                    <TableCell className="text-right">
                      {h.holder_count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {h.share_count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {h.holding_ratio.toFixed(2)}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
