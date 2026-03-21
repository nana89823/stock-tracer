"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

interface Notification {
  id: number;
  alert_id: number | null;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export function useNotifications() {
  const { user } = useAuth();
  const [hasUnread, setHasUnread] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;
    try {
      const res = await api.get("/api/notifications/unread-count");
      setHasUnread(res.data.count > 0);
    } catch (err: any) {
      if (err?.response?.status === 401) {
        // Stop polling on auth failure
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    }
  }, [user]);

  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const res = await api.get("/api/notifications/", { params: { limit: 50 } });
      setNotifications(res.data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [user]);

  const markRead = useCallback(async (id: number) => {
    try {
      await api.patch(`/api/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      // Re-check unread count
      fetchUnreadCount();
    } catch {}
  }, [fetchUnreadCount]);

  const markAllRead = useCallback(async () => {
    try {
      await api.post("/api/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setHasUnread(false);
    } catch {}
  }, []);

  // Initial fetch + polling
  useEffect(() => {
    if (!user) return;

    fetchUnreadCount();
    intervalRef.current = setInterval(fetchUnreadCount, 60000); // 60s polling

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [user, fetchUnreadCount]);

  return {
    hasUnread,
    notifications,
    loading,
    fetchNotifications,
    markRead,
    markAllRead,
  };
}
