"use client";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { LogOut, Menu, Sun, Moon } from "lucide-react";

function getPageTitle(pathname: string): string {
  if (pathname === "/") return "市場總覽";
  if (pathname.startsWith("/stocks/")) return "個股分析";
  if (pathname === "/backtests/new") return "新增回測";
  if (pathname === "/backtests") return "回測列表";
  if (pathname.startsWith("/backtests/")) return "回測詳情";
  return "Stock Tracer";
}

interface HeaderProps {
  onMenuClick: () => void;
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const pageTitle = getPageTitle(pathname);
  const initial = user?.username?.charAt(0)?.toUpperCase() ?? "U";

  return (
    <header className="h-14 md:h-16 border-b border-border bg-background shadow-sm flex items-center justify-between px-4 md:px-6 sticky top-0 z-10">
      {/* Left: menu + title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="md:hidden p-1.5 -ml-1.5 text-muted-foreground hover:text-foreground"
        >
          <Menu className="h-5 w-5" />
        </button>
        <h1 className="text-base md:text-lg font-semibold text-foreground truncate">
          {pageTitle}
        </h1>
      </div>

      {/* User section */}
      {user && (
        <div className="flex items-center gap-2 md:gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="text-muted-foreground hover:text-foreground px-2"
            aria-label="Toggle dark mode"
          >
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
          </Button>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 md:h-8 md:w-8 items-center justify-center rounded-full bg-slate-200 dark:bg-slate-700">
              <span className="text-xs md:text-sm font-semibold text-slate-700 dark:text-slate-200">
                {initial}
              </span>
            </div>
            <span className="hidden sm:inline text-sm font-medium text-foreground">
              {user.username}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="text-muted-foreground hover:text-foreground gap-1.5 px-2 md:px-3"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">登出</span>
          </Button>
        </div>
      )}
    </header>
  );
}
