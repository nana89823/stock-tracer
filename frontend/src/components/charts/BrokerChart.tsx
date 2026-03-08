"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import type { BrokerTrading } from "@/types";

interface Props {
  data: BrokerTrading[];
}

export default function BrokerChart({ data }: Props) {
  // Aggregate by broker: net = buy - sell
  const brokerMap = new Map<
    string,
    { broker_name: string; buy: number; sell: number }
  >();

  for (const d of data) {
    const key = d.broker_id;
    const existing = brokerMap.get(key);
    if (existing) {
      existing.buy += d.buy_volume;
      existing.sell += d.sell_volume;
    } else {
      brokerMap.set(key, {
        broker_name: d.broker_name,
        buy: d.buy_volume,
        sell: d.sell_volume,
      });
    }
  }

  // Sort by net volume (descending) and take top 20
  const chartData = Array.from(brokerMap.entries())
    .map(([id, v]) => ({
      broker: `${id} ${v.broker_name}`,
      淨買超: v.buy - v.sell,
      買進: v.buy,
      賣出: v.sell,
    }))
    .sort((a, b) => b.淨買超 - a.淨買超)
    .slice(0, 20);

  return (
    <ResponsiveContainer width="100%" height={500}>
      <BarChart data={chartData} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis type="number" tick={{ fontSize: 11 }} />
        <YAxis
          dataKey="broker"
          type="category"
          width={120}
          tick={{ fontSize: 10 }}
        />
        <Tooltip
          formatter={(value, name) => [
            `${Number(value).toLocaleString()} 股`,
            name,
          ]}
        />
        <ReferenceLine x={0} stroke="#666" />
        <Bar dataKey="淨買超" name="淨買超">
          {chartData.map((entry, index) => (
            <Cell
              key={index}
              fill={entry.淨買超 >= 0 ? "#ef4444" : "#22c55e"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
