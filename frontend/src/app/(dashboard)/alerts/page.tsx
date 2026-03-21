"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Bell, Plus, Trash2, Power } from "lucide-react";
import { toast } from "sonner";

interface Alert {
  id: number;
  stock_id: string;
  stock_name: string | null;
  condition_type: string;
  threshold: number;
  is_active: boolean;
  is_triggered: boolean;
  created_at: string;
  updated_at: string;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formStockId, setFormStockId] = useState("");
  const [formCondition, setFormCondition] = useState<"above" | "below">("above");
  const [formThreshold, setFormThreshold] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchAlerts = useCallback(() => {
    setLoading(true);
    api.get("/api/alerts/")
      .then((res) => setAlerts(res.data))
      .catch(() => toast.error("載入提醒失敗"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formStockId.trim() || !formThreshold.trim()) return;

    const threshold = parseFloat(formThreshold);
    if (isNaN(threshold) || threshold <= 0) {
      toast.error("請輸入有效的目標價");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/api/alerts/", {
        stock_id: formStockId.trim(),
        condition_type: formCondition,
        threshold,
      });
      toast.success("提醒已建立");
      setDialogOpen(false);
      setFormStockId("");
      setFormThreshold("");
      fetchAlerts();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "建立失敗";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggle = async (alert: Alert) => {
    const prev = alerts;
    setAlerts(alerts.map((a) =>
      a.id === alert.id ? { ...a, is_active: !a.is_active } : a
    ));
    try {
      await api.patch(`/api/alerts/${alert.id}`, {
        is_active: !alert.is_active,
      });
    } catch {
      setAlerts(prev);
      toast.error("更新失敗");
    }
  };

  const handleDelete = async (id: number) => {
    const prev = alerts;
    setAlerts(alerts.filter((a) => a.id !== id));
    try {
      await api.delete(`/api/alerts/${id}`);
      toast("提醒已刪除");
    } catch {
      setAlerts(prev);
      toast.error("刪除失敗");
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-20">
          <p className="text-muted-foreground text-center">載入中...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">提醒管理</h2>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={
              <Button size="sm" className="gap-1.5">
                <Plus className="h-4 w-4" />
                新增提醒
              </Button>
            }
          />
          <DialogContent>
            <DialogHeader>
              <DialogTitle>新增收盤價提醒</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">股票代號</label>
                <Input
                  placeholder="例如 2330"
                  value={formStockId}
                  onChange={(e) => setFormStockId(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">條件</label>
                <Select
                  value={formCondition}
                  onValueChange={(v) => setFormCondition(v as "above" | "below")}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="above">{"漲破（收盤價 ≥）"}</SelectItem>
                    <SelectItem value="below">{"跌破（收盤價 ≤）"}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">目標價</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="例如 850.00"
                  value={formThreshold}
                  onChange={(e) => setFormThreshold(e.target.value)}
                  required
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "建立中..." : "建立提醒"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {alerts.length === 0 ? (
        <Card>
          <CardContent className="py-20 flex flex-col items-center gap-4">
            <Bell className="h-12 w-12 text-muted-foreground/30" />
            <p className="text-lg text-muted-foreground">尚無提醒</p>
            <p className="text-sm text-muted-foreground">
              設定收盤價提醒，當股票收盤價達到目標價時會通知你
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>股票</TableHead>
                  <TableHead>條件</TableHead>
                  <TableHead className="text-right">目標價</TableHead>
                  <TableHead>狀態</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.map((alert) => (
                  <TableRow key={alert.id}>
                    <TableCell>
                      <div>
                        <span className="font-mono">{alert.stock_id}</span>
                        {alert.stock_name && (
                          <span className="text-muted-foreground ml-1.5 text-sm">
                            {alert.stock_name}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {alert.condition_type === "above" ? "漲破" : "跌破"}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      ${alert.threshold.toFixed(2)}
                    </TableCell>
                    <TableCell>
                      {alert.is_triggered ? (
                        <Badge variant="secondary">已觸發</Badge>
                      ) : alert.is_active ? (
                        <Badge variant="default">監控中</Badge>
                      ) : (
                        <Badge variant="outline">已停用</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleToggle(alert)}
                          className={alert.is_active ? "text-primary" : "text-muted-foreground"}
                          title={alert.is_active ? "停用" : "啟用"}
                        >
                          <Power className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(alert.id)}
                          className="text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
