"use client";

import { Bell, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Notification {
  id: number;
  alert_id: number | null;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

interface NotificationPanelProps {
  notifications: Notification[];
  loading: boolean;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diff = Math.floor((now - date) / 1000);

  if (diff < 60) return "剛剛";
  if (diff < 3600) return `${Math.floor(diff / 60)} 分鐘前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小時前`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;
  return new Date(dateStr).toLocaleDateString("zh-TW");
}

export default function NotificationPanel({
  notifications,
  loading,
  onMarkRead,
  onMarkAllRead,
}: NotificationPanelProps) {
  if (loading) {
    return (
      <div className="p-6 text-center text-sm text-muted-foreground">
        載入中...
      </div>
    );
  }

  if (notifications.length === 0) {
    return (
      <div className="p-6 flex flex-col items-center gap-2 text-muted-foreground">
        <Bell className="h-8 w-8 opacity-30" />
        <p className="text-sm">暫無通知</p>
      </div>
    );
  }

  const hasUnread = notifications.some((n) => !n.is_read);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h3 className="text-sm font-semibold">通知</h3>
        {hasUnread && (
          <Button variant="ghost" size="sm" onClick={onMarkAllRead} className="text-xs h-7">
            <Check className="h-3 w-3 mr-1" />
            全部已讀
          </Button>
        )}
      </div>

      {/* List */}
      <div className="divide-y">
        {notifications.map((notif) => (
          <button
            key={notif.id}
            onClick={() => {
              if (!notif.is_read) onMarkRead(notif.id);
            }}
            className={cn(
              "w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors",
              !notif.is_read && "bg-primary/5"
            )}
          >
            <div className="flex items-start gap-2">
              {!notif.is_read && (
                <span className="mt-1.5 h-2 w-2 rounded-full bg-destructive shrink-0" />
              )}
              <div className={cn("flex-1 min-w-0", notif.is_read && "ml-4")}>
                <p className="text-sm font-medium truncate">{notif.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {timeAgo(notif.created_at)} {notif.message && `| ${notif.message}`}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
