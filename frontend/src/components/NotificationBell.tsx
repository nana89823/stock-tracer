"use client";

import { useState } from "react";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import NotificationPanel from "./NotificationPanel";
import { useNotifications } from "@/hooks/useNotifications";

export default function NotificationBell() {
  const {
    hasUnread,
    notifications,
    loading,
    fetchNotifications,
    markRead,
    markAllRead,
  } = useNotifications();
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);

  const handlePopoverOpen = (isOpen: boolean) => {
    setPopoverOpen(isOpen);
    if (isOpen) fetchNotifications();
  };

  const handleSheetOpen = (isOpen: boolean) => {
    setSheetOpen(isOpen);
    if (isOpen) fetchNotifications();
  };

  const bellButton = (
    <Button
      variant="ghost"
      size="sm"
      className="relative text-muted-foreground hover:text-foreground px-2"
      aria-label="通知"
    >
      <Bell className="h-4 w-4" />
      {hasUnread && (
        <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-destructive" />
      )}
    </Button>
  );

  const panel = (
    <NotificationPanel
      notifications={notifications}
      loading={loading}
      onMarkRead={markRead}
      onMarkAllRead={markAllRead}
    />
  );

  // Desktop: Popover, Mobile: Sheet
  return (
    <>
      {/* Desktop */}
      <div className="hidden md:block">
        <Popover open={popoverOpen} onOpenChange={handlePopoverOpen}>
          <PopoverTrigger render={bellButton} />
          <PopoverContent className="w-80 md:w-96 p-0 max-h-[70vh] overflow-auto" align="end">
            {panel}
          </PopoverContent>
        </Popover>
      </div>

      {/* Mobile */}
      <div className="md:hidden">
        <Sheet open={sheetOpen} onOpenChange={handleSheetOpen}>
          <SheetTrigger render={bellButton} />
          <SheetContent side="bottom" className="max-h-[70vh] overflow-auto">
            <SheetHeader>
              <SheetTitle>通知</SheetTitle>
            </SheetHeader>
            {panel}
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
