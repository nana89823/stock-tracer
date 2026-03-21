import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw, Globe, Database, Code } from "lucide-react";

const advantages = [
  {
    icon: RefreshCw,
    title: "每日自動更新",
    description: "排程爬蟲自動抓取最新資料，不需手動操作",
  },
  {
    icon: Globe,
    title: "全市場覆蓋",
    description: "涵蓋上市（TWSE）及上櫃（TPEX）全部股票",
  },
  {
    icon: Database,
    title: "資料來源可靠",
    description: "TWSE、TPEX、TDCC 官方公開資料",
  },
  {
    icon: Code,
    title: "開源透明",
    description: "完整原始碼公開，歡迎貢獻",
  },
];

export default function Advantages() {
  return (
    <section id="advantages" className="bg-muted/30 py-20">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold tracking-tight text-center mb-12">
          為什麼選擇 Stock Tracer
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {advantages.map((item) => (
            <Card key={item.title} className="border-0 shadow-sm">
              <CardHeader>
                <item.icon className="h-10 w-10 text-primary mb-2" />
                <CardTitle className="text-lg">{item.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">{item.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
