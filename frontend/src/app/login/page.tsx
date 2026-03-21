"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      router.push("/home");
    } catch {
      setError("登入失敗，請檢查帳號密碼");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-900 to-slate-800">
      <Card className="w-full max-w-sm shadow-xl">
        <CardHeader className="space-y-2">
          <div className="flex justify-center">
            <TrendingUp className="h-10 w-10 text-primary" />
          </div>
          <CardTitle className="text-center text-2xl">Stock Tracer</CardTitle>
          <p className="text-center text-sm text-muted-foreground">台股追蹤分析平台</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <p className="text-sm text-destructive text-center">{error}</p>
            )}
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium">
                帳號
              </label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                密碼
              </label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "登入中..." : "登入"}
            </Button>
            <p className="text-sm text-center text-muted-foreground">
              還沒有帳號？{" "}
              <Link href="/register" className="text-primary underline">
                註冊
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
