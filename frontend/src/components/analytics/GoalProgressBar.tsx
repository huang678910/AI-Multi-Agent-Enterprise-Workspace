"use client";

interface GoalProgressBarProps {
  title: string;
  progressPct: number;
  currentValue?: number;
  targetValue?: number;
  status: string;
  type?: string;
  direction?: string;  // "higher" or "lower"
}

export default function GoalProgressBar({ title, progressPct, currentValue, targetValue, status, type, direction }: GoalProgressBarProps) {
  const isLowerBetter = direction === "lower";
  const barColor = isLowerBetter
    ? (progressPct >= 100 ? "bg-green-500" : progressPct >= 70 ? "bg-amber-500" : "bg-red-500")
    : (progressPct >= 80 ? "bg-green-500" : progressPct >= 50 ? "bg-blue-500" : progressPct >= 25 ? "bg-amber-500" : "bg-red-500");
  const statusColor = status === "active" ? "bg-blue-50 text-blue-600" : status === "completed" ? "bg-green-50 text-green-600" : "bg-gray-50 text-gray-500";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">{title}</span>
          {type && <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{type}</span>}
          <span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColor}`}>{status}</span>
        </div>
        <span className="text-sm font-semibold text-gray-800">{progressPct}%</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }}
        />
      </div>
      {currentValue != null && targetValue != null && (
        <p className="text-[10px] text-gray-400">
          {currentValue.toLocaleString()} / {targetValue.toLocaleString()}
        </p>
      )}
    </div>
  );
}
