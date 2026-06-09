"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import {
  listGoals, createGoal, deleteGoal,
  listKPIs, createKPI, updateKPI, deleteKPI,
  type GoalData, type KPIData,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2 } from "lucide-react";
import WorkspaceSelector from "@/components/layout/WorkspaceSelector";

export default function GoalsSettingsPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const [tab, setTab] = useState<"goals" | "kpis">("goals");
  const [error, setError] = useState("");

  const [goals, setGoals] = useState<GoalData[]>([]);
  const [newGoal, setNewGoal] = useState({ title: "", type: "KPI", target_value: "", current_value: "" });
  const [savingGoal, setSavingGoal] = useState(false);

  const [kpis, setKPIs] = useState<KPIData[]>([]);
  const [newKPI, setNewKPI] = useState({ name: "", category: "", current_value: "", target_value: "", unit: "", period: "" });
  const [savingKPI, setSavingKPI] = useState(false);
  const [editKPI, setEditKPI] = useState<Record<string, { current_value: string; target_value: string }>>({});

  useEffect(() => { if (!token) router.push("/login"); }, [token, router]);

  useEffect(() => { setGoals([]); setKPIs([]); setError(""); }, [workspaceId]);

  const loadAll = useCallback(async () => {
    if (!workspaceId) return;
    try { setGoals(await listGoals(workspaceId)); } catch {}
    try { setKPIs(await listKPIs(workspaceId)); } catch {}
  }, [workspaceId]);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Auto-calculate progress from current/target values
  const calcProgress = (current: string, target: string): number => {
    const c = parseFloat(current);
    const t = parseFloat(target);
    if (!t || t === 0) return 0;
    return Math.min(100, Math.round((c / t) * 100));
  };

  const handleCreateGoal = async () => {
    if (!workspaceId) return;
    if (!newGoal.title.trim()) { setError("Goal title is required"); return; }
    setSavingGoal(true);
    setError("");
    try {
      const progress = calcProgress(newGoal.current_value, newGoal.target_value);
      await createGoal(workspaceId, {
        title: newGoal.title,
        type: newGoal.type,
        target_value: newGoal.target_value ? parseFloat(newGoal.target_value) : null,
        current_value: newGoal.current_value ? parseFloat(newGoal.current_value) : null,
        progress_pct: progress,
      });
      setNewGoal({ title: "", type: "KPI", target_value: "", current_value: "" });
      loadAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create goal";
      setError(msg);
      console.error("[Goals] Create error:", err);
    } finally {
      setSavingGoal(false);
    }
  };

  const handleCreateKPI = async () => {
    if (!workspaceId) return;
    if (!newKPI.name.trim()) { setError("KPI name is required"); return; }
    setSavingKPI(true);
    setError("");
    try {
      await createKPI(workspaceId, {
        name: newKPI.name,
        category: newKPI.category || undefined,
        current_value: newKPI.current_value ? parseFloat(newKPI.current_value) : null,
        target_value: newKPI.target_value ? parseFloat(newKPI.target_value) : null,
        unit: newKPI.unit || undefined,
        period: newKPI.period || undefined,
      });
      setNewKPI({ name: "", category: "", current_value: "", target_value: "", unit: "", period: "" });
      loadAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create KPI";
      setError(msg);
    } finally {
      setSavingKPI(false);
    }
  };

  if (!workspaceId) return <div className="p-8 text-gray-400 text-center">Select a workspace first.</div>;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <WorkspaceSelector />
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Goals & KPIs</h2>
        <p className="text-sm text-gray-500 mt-1">Track company objectives and key performance indicators.</p>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {(["goals", "kpis"] as const).map((t) => (
          <button key={t} onClick={() => { setTab(t); setError(""); }}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? "bg-white text-gray-800 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}>
            {t === "goals" ? "Goals (OKR/KPI)" : "KPIs"}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Goals */}
      {tab === "goals" && (
        <Card>
          <CardHeader><CardTitle className="text-base">Company Goals</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2 flex-wrap">
              <Input placeholder="Goal title" value={newGoal.title}
                onChange={(e) => { setNewGoal({ ...newGoal, title: e.target.value }); setError(""); }}
                className="flex-1 min-w-[200px]" />
              <select value={newGoal.type} onChange={(e) => setNewGoal({ ...newGoal, type: e.target.value })}
                className="text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white">
                <option value="KPI">KPI</option><option value="OKR">OKR</option><option value="MBO">MBO</option>
              </select>
              <Input placeholder="Target" type="number" value={newGoal.target_value}
                onChange={(e) => setNewGoal({ ...newGoal, target_value: e.target.value })} className="w-24" />
              <Input placeholder="Current" type="number" value={newGoal.current_value}
                onChange={(e) => setNewGoal({ ...newGoal, current_value: e.target.value })} className="w-24" />
              <Button size="sm" onClick={handleCreateGoal} disabled={savingGoal}>
                <Plus size={14} className="mr-1" /> {savingGoal ? "Adding..." : "Add"}
              </Button>
            </div>
            {goals.map((g) => (
              <div key={g.id} className="p-3 rounded border border-gray-100 hover:bg-gray-50 group">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{g.title}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      g.type === "OKR" ? "bg-blue-50 text-blue-600" : g.type === "MBO" ? "bg-purple-50 text-purple-600" : "bg-green-50 text-green-600"
                    }`}>{g.type}</span>
                    <button onClick={async () => { if (!workspaceId || !confirm("Delete?")) return; await deleteGoal(workspaceId, g.id); loadAll(); }}
                      className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded"><Trash2 size={12} className="text-red-400" /></button>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-2">
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${Math.min(100, g.progress_pct || 0)}%` }} />
                  </div>
                  <span className="text-xs text-gray-500 w-10 text-right">{g.progress_pct || 0}%</span>
                </div>
                <div className="flex gap-4 mt-1 text-xs text-gray-400">
                  {g.target_value != null && <span>Target: {g.target_value}</span>}
                  {g.current_value != null && <span>Current: {g.current_value}</span>}
                  <span>{g.status}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* KPIs */}
      {tab === "kpis" && (
        <Card>
          <CardHeader><CardTitle className="text-base">Key Performance Indicators</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2 flex-wrap">
              <Input placeholder="KPI name" value={newKPI.name}
                onChange={(e) => { setNewKPI({ ...newKPI, name: e.target.value }); setError(""); }}
                className="flex-1 min-w-[150px]" />
              <Input placeholder="Category" value={newKPI.category}
                onChange={(e) => setNewKPI({ ...newKPI, category: e.target.value })} className="w-32" />
              <Input placeholder="Current" type="number" value={newKPI.current_value}
                onChange={(e) => setNewKPI({ ...newKPI, current_value: e.target.value })} className="w-24" />
              <Input placeholder="Target" type="number" value={newKPI.target_value}
                onChange={(e) => setNewKPI({ ...newKPI, target_value: e.target.value })} className="w-24" />
              <Input placeholder="Unit" value={newKPI.unit}
                onChange={(e) => setNewKPI({ ...newKPI, unit: e.target.value })} className="w-20" />
              <Input placeholder="Period" value={newKPI.period}
                onChange={(e) => setNewKPI({ ...newKPI, period: e.target.value })} className="w-24" />
              <Button size="sm" onClick={handleCreateKPI} disabled={savingKPI}>
                <Plus size={14} className="mr-1" /> {savingKPI ? "Adding..." : "Add"}
              </Button>
            </div>
            {kpis.map((k) => (
              <div key={k.id} className="flex items-center gap-2 p-3 rounded border border-gray-100 hover:bg-gray-50 group">
                <span className="flex-1 text-sm font-medium">{k.name}</span>
                <span className="text-xs text-gray-400">{k.category}</span>
                {editKPI[k.id] ? (
                  <div className="flex items-center gap-1">
                    <Input type="number" value={editKPI[k.id].current_value}
                      onChange={(e) => setEditKPI({ ...editKPI, [k.id]: { ...editKPI[k.id], current_value: e.target.value } })}
                      className="w-20 h-7 text-xs" />
                    <Input type="number" value={editKPI[k.id].target_value}
                      onChange={(e) => setEditKPI({ ...editKPI, [k.id]: { ...editKPI[k.id], target_value: e.target.value } })}
                      className="w-20 h-7 text-xs" />
                    <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={async () => {
                      if (!workspaceId) return;
                      const e = editKPI[k.id];
                      await updateKPI(workspaceId, k.id, {
                        current_value: e.current_value ? parseFloat(e.current_value) : null,
                        target_value: e.target_value ? parseFloat(e.target_value) : null,
                      });
                      const next = { ...editKPI }; delete next[k.id]; setEditKPI(next);
                      loadAll();
                    }}>Save</Button>
                  </div>
                ) : (
                  <span className="text-xs text-gray-500">
                    {k.current_value}{k.unit} / {k.target_value}{k.unit}
                  </span>
                )}
                <Button size="sm" variant="ghost" className="h-7 text-xs opacity-0 group-hover:opacity-100"
                  onClick={() => setEditKPI({ ...editKPI, [k.id]: { current_value: k.current_value?.toString() || "", target_value: k.target_value?.toString() || "" } })}>
                  Edit
                </Button>
                <button onClick={async () => { if (!workspaceId || !confirm("Delete?")) return; await deleteKPI(workspaceId, k.id); loadAll(); }}
                  className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded"><Trash2 size={12} className="text-red-400" /></button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
