"use client";

import { useState, useEffect } from "react";
import { Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import api from "@/lib/api";
import Link from "next/link";

interface WatchlistButtonProps {
  stockId: string;
}

export default function WatchlistButton({ stockId }: WatchlistButtonProps) {
  const [isWatched, setIsWatched] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/api/watchlist/check/${stockId}`)
      .then((res) => setIsWatched(res.data.is_watched))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [stockId]);

  const toggle = async () => {
    const prev = isWatched;
    setIsWatched(!prev); // Optimistic update

    try {
      if (prev) {
        await api.delete(`/api/watchlist/${stockId}`);
        toast("已從自選股移除");
      } else {
        await api.post("/api/watchlist/", { stock_id: stockId });
        toast("已加入自選股", {
          action: {
            label: "前往自選股",
            onClick: () => window.location.href = "/watchlist",
          },
        });
      }
    } catch {
      setIsWatched(prev); // Revert on error
      toast.error(prev ? "移除失敗" : "加入失敗");
    }
  };

  if (loading) return null;

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      className="active:scale-90 transition-transform duration-100"
      aria-label={isWatched ? "從自選股移除" : "加入自選股"}
    >
      <Star
        className={`h-5 w-5 ${
          isWatched
            ? "fill-amber-400 text-amber-400"
            : "text-muted-foreground"
        }`}
      />
    </Button>
  );
}
