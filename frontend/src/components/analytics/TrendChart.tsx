"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface DataPoint {
  period: string;
  value: number;
}

interface TrendChartProps {
  data: DataPoint[];
  metricName: string;
  color?: string;
  height?: number;
  targetValue?: number;
}

export default function TrendChart({ data, metricName, color = "#3b82f6", height = 250, targetValue }: TrendChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center bg-gray-50 rounded-lg" style={{ height }}>
        <p className="text-sm text-gray-400">No trend data available</p>
      </div>
    );
  }

  // Transform for target line overlay
  const chartData = targetValue != null
    ? data.map((d) => ({ ...d, target: targetValue }))
    : data;

  return (
    <div>
      <p className="text-xs text-gray-500 mb-2 font-medium">{metricName}</p>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke="#9ca3af" />
          <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" width={60} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
            formatter={(value: number) => [value.toLocaleString(), metricName]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
          {targetValue != null && (
            <Line
              type="monotone"
              dataKey="target"
              stroke="#f59e0b"
              strokeDasharray="5 5"
              strokeWidth={1.5}
              dot={false}
              name="Target"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
