"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Star, Trash2, Search } from "lucide-react";
import { toast } from "sonner";

interface WatchlistItem {
  id: number;
  stock_id: string;
  stock_name: string;
  market_type: string;
  close_price: number | null;
  price_change: number | null;
  change_percent: number | null;
  sort_order: number;
  created_at: string;
}

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchWatchlist = () => {
    setLoading(true);
    api.get("/api/watchlist/")
      .then((res) => setItems(res.data))
      .catch(() => toast.error("載入自選股失敗"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const handleRemove = async (stockId: string) => {
    const prev = items;
    setItems(items.filter((item) => item.stock_id !== stockId)); // Optimistic
    try {
      await api.delete(`/api/watchlist/${stockId}`);
      toast("已從自選股移除");
    } catch {
      setItems(prev); // Revert
      toast.error("移除失敗");
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-20">
          <p className="text-muted-foreground text-center">載入中...</p>
        </CardContent>
      </Card>
    );
  }

  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="py-20 flex flex-col items-center gap-4">
          <Star className="h-12 w-12 text-muted-foreground/30" />
          <p className="text-lg text-muted-foreground">尚無自選股</p>
          <Link href="/">
            <Button variant="outline" className="gap-2">
              <Search className="h-4 w-4" />
              前往搜尋股票
            </Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>自選股清單</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>代號</TableHead>
              <TableHead>名稱</TableHead>
              <TableHead>市場</TableHead>
              <TableHead className="text-right">收盤價</TableHead>
              <TableHead className="text-right">漲跌幅</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => {
              const isUp = (item.price_change ?? 0) >= 0;
              return (
                <TableRow key={item.stock_id}>
                  <TableCell>
                    <Link
                      href={`/stocks/${item.stock_id}`}
                      className="text-primary hover:underline font-mono"
                    >
                      {item.stock_id}
                    </Link>
                  </TableCell>
                  <TableCell>{item.stock_name}</TableCell>
                  <TableCell>
                    <span className="text-xs text-muted-foreground">
                      {item.market_type === "tpex" ? "上櫃" : "上市"}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {item.close_price != null
                      ? item.close_price.toFixed(2)
                      : "-"}
                  </TableCell>
                  <TableCell
                    className={`text-right font-mono ${
                      item.price_change != null
                        ? isUp
                          ? "text-stock-up"
                          : "text-stock-down"
                        : ""
                    }`}
                  >
                    {item.change_percent != null
                      ? `${isUp ? "+" : ""}${item.change_percent.toFixed(2)}%`
                      : "-"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemove(item.stock_id)}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
