"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import { listMetrics, recordMetric, batchRecordMetrics, deleteMetric, getMetricSnapshot } from "@/lib/api-client";
import type { MetricData } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import WorkspaceSelector from "@/components/layout/WorkspaceSelector";
import { Plus, Trash2, Upload } from "lucide-react";

const CATEGORIES = ["revenue", "cost", "inventory", "hr", "operations", "custom"];
const METRIC_PRESETS = [
  { name: "revenue", unit: "USD", category: "revenue" },
  { name: "orders", unit: "units", category: "revenue" },
  { name: "cogs", unit: "USD", category: "cost" },
  { name: "marketing_spend", unit: "USD", category: "cost" },
  { name: "inventory_level", unit: "units", category: "inventory" },
  { name: "headcount", unit: "people", category: "hr" },
  { name: "customer_satisfaction", unit: "%", category: "custom" },
  { name: "profit_margin", unit: "%", category: "revenue" },
];

function getPeriod(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function MetricsPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const [metrics, setMetrics] = useState<MetricData[]>([]);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [snapshot, setSnapshot] = useState<MetricData[]>([]);

  // Form state
  const [form, setForm] = useState({ metric_name: "", metric_value: "", unit: "", period: getPeriod(), category: "", notes: "" });
  const [jsonInput, setJsonInput] = useState("");
  const [jsonError, setJsonError] = useState("");

  useEffect(() => { if (!token) router.push("/login"); }, [token, router]);
  useEffect(() => { setMetrics([]); setSnapshot([]); }, [workspaceId]);

  const loadData = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await listMetrics(workspaceId, categoryFilter || undefined);
      setMetrics(data);
      const snap = await getMetricSnapshot(workspaceId);
      setSnapshot(snap.metrics);
    } catch {}
  }, [workspaceId, categoryFilter]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSubmit = async () => {
    if (!workspaceId || !form.metric_name.trim() || !form.metric_value) return;
    try {
      await recordMetric(workspaceId, {
        metric_name: form.metric_name.trim(),
        metric_value: parseFloat(form.metric_value),
        unit: form.unit || undefined,
        period: form.period || undefined,
        category: form.category || undefined,
        notes: form.notes || undefined,
      });
      setForm({ metric_name: "", metric_value: "", unit: "", period: getPeriod(), category: "", notes: "" });
      loadData();
    } catch {}
  };

  const handleBatchImport = async () => {
    if (!workspaceId || !jsonInput.trim()) return;
    setJsonError("");
    try {
      const parsed = JSON.parse(jsonInput);
      const arr = Array.isArray(parsed) ? parsed : [parsed];
      await batchRecordMetrics(workspaceId, arr.map((m: Record<string, unknown>) => ({
        metric_name: String(m.metric_name || m.name || ""),
        metric_value: Number(m.metric_value || m.value || 0),
        unit: m.unit ? String(m.unit) : undefined,
        period: m.period ? String(m.period) : undefined,
        category: m.category ? String(m.category) : undefined,
        notes: m.notes ? String(m.notes) : undefined,
      })));
      setJsonInput("");
      loadData();
    } catch {
      setJsonError("Invalid JSON format. Expect: [{\"metric_name\":\"revenue\",\"metric_value\":150000,\"unit\":\"USD\",\"period\":\"2026-06\"}]");
    }
  };

  const handleDelete = async (id: string) => {
    if (!workspaceId || !confirm("Delete this metric entry? (Admin only)")) return;
    try { await deleteMetric(workspaceId, id); loadData(); }
    catch { alert("Delete failed — admin role required"); }
  };

  const handlePresetSelect = (preset: typeof METRIC_PRESETS[number]) => {
    setForm({
      metric_name: preset.name,
      metric_value: form.metric_value,
      unit: preset.unit,
      period: form.period || getPeriod(),
      category: preset.category,
      notes: form.notes,
    });
  };

  if (!workspaceId) return <div className="p-8 text-gray-400">Select a workspace first.</div>;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <WorkspaceSelector />
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Business Metrics</h2>
        <p className="text-sm text-gray-500 mt-1">Digital Twin — record and manage business performance indicators.</p>
      </div>

      {/* Snapshot Cards */}
      {snapshot.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {snapshot.map((m) => (
            <Card key={m.id} className="hover:shadow-sm transition-shadow">
              <CardContent className="p-3">
                <p className="text-[10px] text-gray-400 uppercase tracking-wide">{m.metric_name}</p>
                <p className="text-lg font-semibold text-gray-800">
                  {m.metric_value.toLocaleString()}
                  {m.unit && <span className="text-xs text-gray-400 ml-1">{m.unit}</span>}
                </p>
                {m.period && <p className="text-[10px] text-gray-400 mt-0.5">{m.period}</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Metric Form */}
      <Card>
        <CardHeader><CardTitle className="text-base">Record Metric</CardTitle></CardHeader>
        <CardContent>
          {/* Preset buttons */}
          <div className="flex flex-wrap gap-1.5 mb-3">
            {METRIC_PRESETS.map((p) => (
              <button key={p.name} onClick={() => handlePresetSelect(p)}
                className="text-[10px] px-2 py-0.5 rounded border border-gray-200 hover:bg-blue-50 hover:border-blue-300 transition-colors text-gray-500">
                {p.name}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <Input placeholder="Metric Name (e.g. revenue)" value={form.metric_name}
              onChange={(e) => setForm({ ...form, metric_name: e.target.value })}
              className="w-36" />
            <Input placeholder="Value" type="number" value={form.metric_value}
              onChange={(e) => setForm({ ...form, metric_value: e.target.value })}
              className="w-24" />
            <Input placeholder="Unit" value={form.unit}
              onChange={(e) => setForm({ ...form, unit: e.target.value })}
              className="w-20" />
            <Input placeholder="Period (2026-06)" value={form.period}
              onChange={(e) => setForm({ ...form, period: e.target.value })}
              className="w-28" />
            <select value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white w-28">
              <option value="">Category</option>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <Input placeholder="Notes (optional)" value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="w-40" />
            <Button size="sm" onClick={handleSubmit} disabled={!form.metric_name.trim() || !form.metric_value}>
              <Plus size={14} className="mr-1" /> Record
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Batch Import */}
      <Card>
        <CardHeader><CardTitle className="text-base">Batch Import (JSON)</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            <textarea
              value={jsonInput}
              onChange={(e) => { setJsonInput(e.target.value); setJsonError(""); }}
              placeholder={`[{"metric_name":"revenue","metric_value":150000,"unit":"USD","period":"2026-06","category":"revenue"},{"metric_name":"orders","metric_value":3200,"unit":"units","period":"2026-06","category":"revenue"}]`}
              rows={4}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {jsonError && <p className="text-xs text-red-600">{jsonError}</p>}
            <Button size="sm" onClick={handleBatchImport} disabled={!jsonInput.trim()}>
              <Upload size={14} className="mr-1" /> Import
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Category Filter + Metric List */}
      <div className="flex gap-2 items-center">
        <select value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); }}
          className="text-sm rounded-lg border border-gray-200 px-3 py-1.5 bg-white">
          <option value="">All Categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="text-xs text-gray-400">{metrics.length} entries</span>
      </div>

      <div className="space-y-2">
        {metrics.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">
            No metrics recorded yet. Use the form above to add your first metric, or paste JSON for batch import.
          </p>
        ) : (
          metrics.map((m) => (
            <Card key={m.id} className="hover:shadow-sm transition-shadow group">
              <CardContent className="p-3 flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-800">{m.metric_name}</span>
                    {m.category && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{m.category}</span>
                    )}
                  </div>
                  <div className="flex gap-3 mt-0.5 text-xs text-gray-400">
                    <span>{m.metric_value.toLocaleString()}{m.unit ? ` ${m.unit}` : ""}</span>
                    {m.period && <span>Period: {m.period}</span>}
                    {m.notes && <span className="truncate max-w-[200px]">📝 {m.notes}</span>}
                  </div>
                </div>
                <span className="text-[10px] text-gray-400 flex-shrink-0">
                  {m.recorded_at ? new Date(m.recorded_at).toLocaleDateString() : ""}
                </span>
                <button
                  onClick={() => handleDelete(m.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 rounded transition-all flex-shrink-0"
                  title="Delete (Admin only)">
                  <Trash2 size={14} className="text-red-400" />
                </button>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
