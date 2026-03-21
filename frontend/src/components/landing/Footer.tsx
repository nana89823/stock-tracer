import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Footer() {
  return (
    <>
      {/* CTA */}
      <section className="py-20 text-center">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold tracking-tight">準備好開始了嗎？</h2>
          <p className="mt-4 text-muted-foreground">免費註冊，立即開始追蹤台股。</p>
          <div className="mt-8">
            <Button size="lg" render={<Link href="/register" />}>
              免費開始使用
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <p>&copy; 2026 Stock Tracer</p>
          <a
            href="https://github.com/nana89823/stock-tracer"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
          >
            GitHub
          </a>
        </div>
      </footer>
    </>
  );
}
