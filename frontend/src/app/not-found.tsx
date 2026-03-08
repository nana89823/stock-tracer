import { AlertTriangle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center p-8">
      <div className="flex flex-col items-center gap-6 max-w-md text-center">
        <div className="rounded-full bg-muted p-4">
          <AlertTriangle className="h-10 w-10 text-muted-foreground" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold tracking-tight">找不到頁面</h2>
          <p className="text-muted-foreground">
            您要找的頁面不存在或已被移除
          </p>
        </div>
        <a
          href="/"
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
        >
          返回首頁
        </a>
      </div>
    </div>
  );
}
