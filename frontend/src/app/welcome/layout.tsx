import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Stock Tracer — 台股追蹤分析平台",
  description: "即時台股追蹤、籌碼分析、回測系統，掌握投資先機。",
};

export default function WelcomeLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
