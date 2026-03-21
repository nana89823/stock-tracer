"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { BarChart3, LineChart, TrendingUp, X } from "lucide-react";

const navItems = [
  { href: "/home", label: "市場總覽", icon: BarChart3 },
  { href: "/backtests", label: "回測", icon: LineChart },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/home" ? pathname === "/home" : pathname.startsWith(href);

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-60 bg-slate-900 text-slate-100 flex flex-col transition-transform duration-200 ease-in-out md:sticky md:top-0 md:h-screen md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="px-5 py-5 border-b border-slate-700/50 flex items-center justify-between">
          <Link href="/home" className="flex items-center gap-2.5" onClick={onClose}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <TrendingUp className="h-4.5 w-4.5 text-white" />
            </div>
            <span className="text-lg font-semibold tracking-tight">
              Stock Tracer
            </span>
          </Link>
          <button onClick={onClose} className="md:hidden p-1 text-slate-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          <p className="px-3 mb-2 text-[11px] font-medium uppercase tracking-wider text-slate-500">
            導覽
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                  active
                    ? "bg-slate-800 text-white border-l-2 border-blue-500"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                )}
              >
                <Icon className={cn("h-[18px] w-[18px]", active ? "text-blue-400" : "text-slate-500")} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Bottom section */}
        <div className="px-5 py-4 border-t border-slate-700/50">
          <p className="text-[11px] text-slate-600">Stock Tracer v1.0</p>
        </div>
      </aside>
    </>
  );
}
