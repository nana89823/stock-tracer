"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import { safeParse, StockListSchema } from "@/lib/schemas";
import { useDebounce } from "@/hooks/useDebounce";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Search, ChevronRight, TrendingUp } from "lucide-react";
import Pagination from "@/components/Pagination";
import SearchResultSkeleton from "@/components/skeletons/SearchResultSkeleton";
import type { Stock } from "@/types";

const PAGE_SIZE = 20;

export default function HomePage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialQuery = searchParams.get("q") || "";
  const [query, setQuery] = useState(initialQuery);
  const debouncedQuery = useDebounce(query, 300);
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  // Reset page when search query changes
  useEffect(() => {
    setPage(1);
  }, [debouncedQuery]);

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setStocks([]);
      setTotalCount(0);
      return;
    }

    setLoading(true);
    setError("");
    api
      .get("/api/stocks/", {
        params: {
          q: debouncedQuery,
          skip: (page - 1) * PAGE_SIZE,
          limit: PAGE_SIZE,
        },
      })
      .then((res) => {
        setStocks(safeParse(StockListSchema, res.data));
        const total = Number(res.headers["x-total-count"] ?? 0);
        setTotalCount(total);
      })
      .catch(() => setError("搜尋失敗，請稍後再試"))
      .finally(() => setLoading(false));
  }, [debouncedQuery, page]);

  return (
    <div className="space-y-8">
      {/* Hero search area */}
      <div className="flex flex-col items-center pt-12 pb-4 gap-6">
        <div className="flex items-center gap-3">
          <TrendingUp className="h-8 w-8 text-primary" />
          <h1 className="text-3xl font-bold tracking-tight">股票追蹤</h1>
        </div>
        <div className="relative w-full max-w-lg">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <Input
            placeholder="輸入股票代號或名稱..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-10 h-12 text-base rounded-xl shadow-sm border-border/60"
          />
        </div>
      </div>

      {loading && <SearchResultSkeleton />}

      {error && (
        <p className="text-destructive text-center">{error}</p>
      )}

      {!loading && !error && stocks.length > 0 && (
      <>
        <Card className="max-w-2xl mx-auto">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-28">代號</TableHead>
                  <TableHead>名稱</TableHead>
                  <TableHead className="w-24">市場</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {stocks.map((stock) => (
                  <TableRow
                    key={stock.stock_id}
                    className="cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => router.push(`/stocks/${stock.stock_id}`)}
                  >
                    <TableCell className="font-mono font-semibold">
                      {stock.stock_id}
                    </TableCell>
                    <TableCell>{stock.stock_name}</TableCell>
                    <TableCell>
                      {stock.market_type === "tpex" ? (
                        <Badge className="bg-amber-500/15 text-amber-700 dark:text-amber-400">
                          上櫃
                        </Badge>
                      ) : (
                        <Badge className="bg-blue-500/15 text-blue-700 dark:text-blue-400">
                          上市
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {totalPages > 1 && (
          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        )}
      </>
      )}

      {!loading && !error && debouncedQuery && stocks.length === 0 && (
        <p className="text-muted-foreground text-center">找不到符合的股票</p>
      )}

      {!debouncedQuery && (
        <div className="text-center mt-8 space-y-3">
          <p className="text-muted-foreground text-sm">
            搜尋台灣上市、上櫃股票，查看即時籌碼分析與技術圖表
          </p>
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground/70">
            <span>熱門搜尋：</span>
            {[
              { id: "2330", name: "台積電" },
              { id: "2317", name: "鴻海" },
              { id: "2454", name: "聯發科" },
            ].map((s) => (
              <button
                key={s.id}
                onClick={() => setQuery(s.id)}
                className="px-2.5 py-1 rounded-md bg-muted hover:bg-muted/80 text-foreground transition-colors"
              >
                {s.id} {s.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
