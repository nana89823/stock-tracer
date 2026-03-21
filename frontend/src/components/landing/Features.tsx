import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart3, PieChart, LineChart, Bell } from "lucide-react";

const features = [
  {
    icon: BarChart3,
    title: "即時行情追蹤",
    description: "上市上櫃股票 K 線圖、成交量、漲跌幅一目瞭然",
  },
  {
    icon: PieChart,
    title: "深度籌碼分析",
    description: "三大法人買賣超、大戶持股、融資融券、分點券商完整呈現",
  },
  {
    icon: LineChart,
    title: "智能回測系統",
    description: "多種內建策略、自訂參數，歷史數據驗證投資想法",
  },
  {
    icon: Bell,
    title: "到價提醒 & 自選",
    description: "設定價格條件，即時通知不漏接",
  },
];

export default function Features() {
  return (
    <section id="features" className="bg-muted/30 py-20">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold tracking-tight text-center mb-12">
          核心功能
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature) => (
            <Card key={feature.title} className="border-0 shadow-sm">
              <CardHeader>
                <feature.icon className="h-10 w-10 text-primary mb-2" />
                <CardTitle className="text-lg">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">{feature.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
