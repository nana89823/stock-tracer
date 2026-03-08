"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { RawChip } from "@/types";

interface Props {
  data: RawChip[];
}

export default function ChipChart({ data }: Props) {
  const chartData = data.map((d) => ({
    date: d.date,
    外資: d.foreign_net,
    投信: d.trust_net,
    自營商: d.dealer_net,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          formatter={(value, name) => [
            `${Number(value).toLocaleString()} 股`,
            name,
          ]}
        />
        <Legend />
        <ReferenceLine y={0} stroke="#666" />
        <Bar dataKey="外資" fill="#3b82f6" stackId="a" />
        <Bar dataKey="投信" fill="#f59e0b" stackId="a" />
        <Bar dataKey="自營商" fill="#8b5cf6" stackId="a" />
      </BarChart>
    </ResponsiveContainer>
  );
}
