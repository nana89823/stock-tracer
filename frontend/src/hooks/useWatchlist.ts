import { useState, useCallback } from "react";
import api from "@/lib/api";
import { toast } from "sonner";

export function useWatchlist() {
  const [checking, setChecking] = useState(false);

  const checkWatched = useCallback(async (stockId: string): Promise<boolean> => {
    try {
      const res = await api.get(`/api/watchlist/check/${stockId}`);
      return res.data.is_watched;
    } catch {
      return false;
    }
  }, []);

  const addToWatchlist = useCallback(async (stockId: string) => {
    await api.post("/api/watchlist/", { stock_id: stockId });
  }, []);

  const removeFromWatchlist = useCallback(async (stockId: string) => {
    await api.delete(`/api/watchlist/${stockId}`);
  }, []);

  return { checkWatched, addToWatchlist, removeFromWatchlist, checking };
}
