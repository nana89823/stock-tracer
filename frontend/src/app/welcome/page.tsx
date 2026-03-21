"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, BarChart3, PieChart, LineChart } from "lucide-react";

const features = [
  {
    icon: BarChart3,
    title: "即時行情追蹤",
    description: "上市上櫃股票即時K線圖、成交量、漲跌幅一目瞭然",
  },
  {
    icon: PieChart,
    title: "深度籌碼分析",
    description: "三大法人買賣超、大戶持股、融資融券、分點券商進出完整呈現",
  },
  {
    icon: LineChart,
    title: "智能回測系統",
    description: "多種內建策略、自訂參數，用歷史數據驗證你的投資想法",
  },
];

export default function WelcomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-muted-foreground">載入中...</p>
      </div>
    );
  }

  if (user) return null;

  const scrollToFeatures = () => {
    const el = document.getElementById("features");
    if (el) {
      el.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
      });
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-primary" />
            <span className="text-lg font-semibold">Stock Tracer</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" render={<Link href="/login" />}>
              登入
            </Button>
            <Button render={<Link href="/register" />}>
              免費開始使用
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="container mx-auto px-4 py-24 md:py-32 lg:py-40 text-center">
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight">
          掌握台股投資先機
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          即時追蹤股票走勢、深度籌碼分析、智能回測系統，助你做出更明智的投資決策。
        </p>
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button size="lg" render={<Link href="/register" />}>
            免費開始使用
          </Button>
          <Button size="lg" variant="outline" onClick={scrollToFeatures}>
            了解更多
          </Button>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="container mx-auto px-4 py-20">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature) => (
            <Card key={feature.title}>
              <CardHeader>
                <feature.icon className="h-10 w-10 text-primary mb-2" />
                <CardTitle>{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">{feature.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h2 className="text-3xl font-bold tracking-tight">準備好開始了嗎？</h2>
        <div className="mt-8">
          <Button size="lg" render={<Link href="/register" />}>
            免費開始使用
          </Button>
        </div>
      </section>
    </div>
  );
}
