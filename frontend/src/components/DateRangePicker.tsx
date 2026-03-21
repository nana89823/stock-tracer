"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { CalendarIcon } from "lucide-react";
import type { DateRange } from "react-day-picker";

interface DateRangePickerProps {
  startDate: string; // "YYYY-MM-DD"
  endDate: string;   // "YYYY-MM-DD"
  onChange: (start: string, end: string) => void;
}

const QUICK_OPTIONS = [
  { label: "近7天", days: 7 },
  { label: "近30天", days: 30 },
  { label: "近90天", days: 90 },
  { label: "近180天", days: 180 },
  { label: "近一年", days: 365 },
] as const;

function formatDate(d: Date): string {
  return d.toISOString().split("T")[0];
}

function daysAgo(days: number): string {
  return formatDate(new Date(Date.now() - days * 24 * 60 * 60 * 1000));
}

export default function DateRangePicker({ startDate, endDate, onChange }: DateRangePickerProps) {
  const [popoverOpen, setPopoverOpen] = useState(false);

  const today = formatDate(new Date());

  const activeQuick = useMemo(() => {
    if (endDate !== today) return null;
    for (const opt of QUICK_OPTIONS) {
      if (startDate === daysAgo(opt.days)) return opt.days;
    }
    return null;
  }, [startDate, endDate, today]);

  const handleQuick = (days: number) => {
    onChange(daysAgo(days), today);
  };

  const handleCalendarSelect = (range: DateRange | undefined) => {
    if (range?.from && range?.to) {
      onChange(formatDate(range.from), formatDate(range.to));
      setPopoverOpen(false);
    }
  };

  const calendarRange: DateRange | undefined = useMemo(() => {
    return {
      from: new Date(startDate + "T00:00:00"),
      to: new Date(endDate + "T00:00:00"),
    };
  }, [startDate, endDate]);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {QUICK_OPTIONS.map((opt) => (
        <Button
          key={opt.days}
          variant={activeQuick === opt.days ? "default" : "outline"}
          size="sm"
          onClick={() => handleQuick(opt.days)}
        >
          {opt.label}
        </Button>
      ))}

      <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
        <PopoverTrigger
          render={
            <Button
              variant={activeQuick === null ? "default" : "outline"}
              size="sm"
            >
              <CalendarIcon className="size-3.5 mr-1" />
              自訂
            </Button>
          }
        />
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="range"
            selected={calendarRange}
            onSelect={handleCalendarSelect}
            weekStartsOn={1}
            disabled={(date) => date > new Date()}
            numberOfMonths={2}
          />
        </PopoverContent>
      </Popover>

      <span className="text-xs text-muted-foreground ml-1">
        {startDate} ~ {endDate}
      </span>
    </div>
  );
}
