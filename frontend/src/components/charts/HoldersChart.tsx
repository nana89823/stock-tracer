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
} from "recharts";
import type { MajorHolder } from "@/types";

interface Props {
  data: MajorHolder[];
}

const LEVEL_LABELS: Record<number, string> = {
  1: "1-999",
  2: "1,000-5,000",
  3: "5,001-10,000",
  4: "10,001-15,000",
  5: "15,001-20,000",
  6: "20,001-30,000",
  7: "30,001-40,000",
  8: "40,001-50,000",
  9: "50,001-100,000",
  10: "100,001-200,000",
  11: "200,001-400,000",
  12: "400,001-600,000",
  13: "600,001-800,000",
  14: "800,001-1,000,000",
  15: "1,000,001以上",
  16: "合計",
};

const COLORS = [
  "#94a3b8", "#64748b", "#475569", "#334155",
  "#3b82f6", "#2563eb", "#1d4ed8", "#1e40af",
  "#f59e0b", "#d97706", "#b45309", "#92400e",
  "#ef4444", "#dc2626", "#b91c1c", "#991b1b",
];

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { level: string; holding_ratio: number; holder_count: number; share_count: number } }> }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-popover border border-border rounded-md p-3 shadow-lg text-sm">
      <p className="font-medium mb-1">{d.level}</p>
      <p>持股比例：{d.holding_ratio.toFixed(2)}%</p>
      <p>人數：{d.holder_count.toLocaleString()} 人</p>
      <p>張數：{d.share_count.toLocaleString()} 張</p>
    </div>
  );
}

export default function HoldersChart({ data }: Props) {
  // Filter out level 16 (合計) from chart, only show levels 1-15
  const chartData = data
    .filter((d) => d.holding_level <= 15)
    .map((d) => ({
      level: LEVEL_LABELS[d.holding_level] || `Level ${d.holding_level}`,
      holding_ratio: d.holding_ratio,
      holder_count: d.holder_count,
      share_count: d.share_count,
    }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis type="number" unit="%" tick={{ fontSize: 11 }} />
        <YAxis
          dataKey="level"
          type="category"
          width={130}
          tick={{ fontSize: 10 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="holding_ratio" name="持股比例">
          {chartData.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
