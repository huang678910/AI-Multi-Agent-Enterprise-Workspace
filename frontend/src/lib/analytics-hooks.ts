"use client";
import { useState, useEffect, useCallback } from "react";
import { getDashboard, triggerAnalysis, getAlerts } from "@/lib/api-client";

interface MetricEntry {
  id: string;
  metric_name: string;
  metric_value: number;
  unit?: string;
  period?: string;
  category?: string;
}

interface TrendData {
  metric_name: string;
  unit?: string;
  data_points: Array<{ period: string; value: number }>;
  change_pct?: number;
  trend_direction?: string;
}

interface AnalysisResult {
  summary: string;
  insights: string[];
  recommendations: string[];
  generated_at: string;
}

interface Alert {
  id: string;
  severity: "critical" | "warning" | "info";
  metric_name: string;
  message: string;
  threshold?: number;
}

interface DashboardData {
  metrics_snapshot: { metrics: MetricEntry[]; generated_at: string };
  trends: Record<string, TrendData>;
  kpis: Array<Record<string, unknown>>;
  goals: Array<Record<string, unknown>>;
  analysis?: AnalysisResult;
  alerts: Alert[];
}

export function useDashboardData(workspaceId: string | null) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getDashboard(workspaceId) as DashboardData;
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, refresh: load };
}

export function useAiAnalysis(workspaceId: string | null) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await triggerAnalysis(workspaceId) as AnalysisResult;
      setAnalysis(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis generation failed");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  return { analysis, loading, error, generate };
}

export function useAlerts(workspaceId: string | null) {
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const load = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const result = await getAlerts(workspaceId) as Alert[];
      setAlerts(result);
    } catch { /* silent */ }
  }, [workspaceId]);

  useEffect(() => { load(); }, [load]);

  return alerts;
}
