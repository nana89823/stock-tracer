"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { BacktestDailyReturn } from "@/types";

interface Props {
  data: BacktestDailyReturn[];
}

export default function EquityCurveChart({ data }: Props) {
  const chartData = data.map((d) => ({
    date: d.date,
    total_equity: d.total_equity,
    daily_return: d.daily_return,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
        <YAxis
          tick={{ fontSize: 12 }}
          tickFormatter={(v) => v.toLocaleString()}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1a1a2e",
            border: "1px solid #333",
            borderRadius: "8px",
          }}
          formatter={(value, name) => {
            const v = Number(value);
            if (name === "total_equity") {
              return [`$${v.toLocaleString()}`, "總資產"];
            }
            if (name === "daily_return") {
              return [
                value !== null ? `${(v * 100).toFixed(2)}%` : "N/A",
                "日報酬率",
              ];
            }
            return [String(value), String(name)];
          }}
          labelFormatter={(label) => `日期: ${label}`}
        />
        <Line
          type="monotone"
          dataKey="total_equity"
          stroke="#3b82f6"
          dot={false}
          strokeWidth={2}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
