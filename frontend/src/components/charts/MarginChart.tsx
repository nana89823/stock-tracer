"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { MarginTrading } from "@/types";

interface Props {
  data: MarginTrading[];
}

export default function MarginChart({ data }: Props) {
  const chartData = data.map((d) => ({
    date: d.date,
    融資餘額: d.margin_balance,
    融券餘額: d.short_balance,
    融資增減: d.margin_buy - d.margin_sell - d.margin_cash_repay,
    融券增減: d.short_sell - d.short_buy - d.short_cash_repay,
    資券互抵: d.offset,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <ComposedChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="balance" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="change" orientation="right" tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value, name) => [
            Number(value).toLocaleString(),
            name,
          ]}
        />
        <Legend />
        <Bar
          yAxisId="change"
          dataKey="融資增減"
          fill="#ef4444"
          opacity={0.7}
        />
        <Bar
          yAxisId="change"
          dataKey="融券增減"
          fill="#22c55e"
          opacity={0.7}
        />
        <Line
          yAxisId="balance"
          type="monotone"
          dataKey="融資餘額"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={false}
        />
        <Line
          yAxisId="balance"
          type="monotone"
          dataKey="融券餘額"
          stroke="#8b5cf6"
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
