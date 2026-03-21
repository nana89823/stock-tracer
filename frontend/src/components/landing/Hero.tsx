import Link from "next/link";
import { Button } from "@/components/ui/button";
import HeroIllustration from "./HeroIllustration";

export default function Hero() {
  return (
    <section className="container mx-auto px-4 py-20 md:py-28 lg:py-36">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        <div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight">
            掌握台股投資先機
          </h1>
          <p className="mt-6 text-lg text-muted-foreground max-w-xl">
            即時行情追蹤、深度籌碼分析、智能回測系統，一站式台股投資分析平台。
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4">
            <Button size="lg" render={<Link href="/register" />}>
              免費開始使用
            </Button>
            <Button size="lg" variant="outline" render={<a href="#features" />}>
              了解更多
            </Button>
          </div>
        </div>
        <div className="flex justify-center lg:justify-end">
          <HeroIllustration />
        </div>
      </div>
    </section>
  );
}
