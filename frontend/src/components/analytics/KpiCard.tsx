"use client";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface KpiCardProps {
  name: string;
  value: number;
  unit?: string;
  changePct?: number | null;
  trendDirection?: string;
  period?: string;
}

export default function KpiCard({ name, value, unit, changePct, trendDirection, period }: KpiCardProps) {
  const formattedValue = value.toLocaleString(undefined, { maximumFractionDigits: 2 });

  return (
    <Card className="hover:shadow-sm transition-shadow">
      <CardContent className="p-4">
        <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-1 truncate">{name}</p>
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-bold text-gray-900">{formattedValue}</span>
          {unit && <span className="text-xs text-gray-400">{unit}</span>}
        </div>
        <div className="flex items-center gap-1.5 mt-1.5">
          {trendDirection === "up" && <TrendingUp size={14} className="text-green-500" />}
          {trendDirection === "down" && <TrendingDown size={14} className="text-red-500" />}
          {trendDirection === "flat" && <Minus size={14} className="text-gray-400" />}
          {changePct != null && (
            <span className={`text-xs font-medium ${
              changePct > 0 ? "text-green-600" : changePct < 0 ? "text-red-600" : "text-gray-500"
            }`}>
              {changePct > 0 ? "+" : ""}{changePct}%
            </span>
          )}
          {period && <span className="text-[10px] text-gray-400 ml-auto">{period}</span>}
        </div>
      </CardContent>
    </Card>
  );
}
