"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import {
  listDepartments, createDepartment, updateDepartment, deleteDepartment,
  listPositions, createPosition, deletePosition,
  listEmployees, createEmployee, deleteEmployee,
  type DeptData, type PosData, type EmpData,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2 } from "lucide-react";
import WorkspaceSelector from "@/components/layout/WorkspaceSelector";

export default function OrgSettingsPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const [tab, setTab] = useState<"dept" | "pos" | "emp">("dept");
  const [error, setError] = useState("");

  // Departments
  const [depts, setDepts] = useState<DeptData[]>([]);
  const [newDept, setNewDept] = useState({ name: "", type: "", parent_id: "" });
  const [savingDept, setSavingDept] = useState(false);
  const [editDept, setEditDept] = useState<Record<string, { name: string; type: string }>>({});

  // Positions
  const [positions, setPositions] = useState<PosData[]>([]);
  const [newPos, setNewPos] = useState({ title: "", level: "", department_id: "" });
  const [savingPos, setSavingPos] = useState(false);

  // Employees
  const [employees, setEmployees] = useState<EmpData[]>([]);
  const [newEmp, setNewEmp] = useState({ name: "", email: "", department_id: "", position_id: "" });
  const [savingEmp, setSavingEmp] = useState(false);

  // Auth guard
  useEffect(() => { if (!token) router.push("/login"); }, [token, router]);

  // Clear data on workspace switch
  useEffect(() => {
    setDepts([]); setPositions([]); setEmployees([]);
    setError("");
  }, [workspaceId]);

  // Load data
  const loadDepts = useCallback(async () => {
    if (!workspaceId) return;
    try { const d = await listDepartments(workspaceId); setDepts(d); } catch {}
  }, [workspaceId]);
  const loadPositions = useCallback(async () => {
    if (!workspaceId) return;
    try { const d = await listPositions(workspaceId); setPositions(d); } catch {}
  }, [workspaceId]);
  const loadEmployees = useCallback(async () => {
    if (!workspaceId) return;
    try { const d = await listEmployees(workspaceId); setEmployees(d); } catch {}
  }, [workspaceId]);

  useEffect(() => { loadDepts(); loadPositions(); loadEmployees(); }, [loadDepts, loadPositions, loadEmployees]);

  // --- Department handlers ---
  const handleCreateDept = async () => {
    if (!workspaceId) return;
    if (!newDept.name.trim()) { setError("Department name is required"); return; }
    setSavingDept(true);
    setError("");
    try {
      console.log("[Org] Creating department:", newDept.name);
      await createDepartment(workspaceId, {
        name: newDept.name, type: newDept.type || undefined,
        parent_id: newDept.parent_id || undefined,
      });
      setNewDept({ name: "", type: "", parent_id: "" });
      loadDepts();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create department";
      setError(msg);
      console.error("[Org] Create dept error:", err);
    } finally {
      setSavingDept(false);
    }
  };

  const handleUpdateDept = async (id: string) => {
    if (!workspaceId) return;
    const e = editDept[id];
    if (!e) return;
    setError("");
    try {
      await updateDepartment(workspaceId, id, { name: e.name, type: e.type || undefined });
      const next = { ...editDept };
      delete next[id];
      setEditDept(next);
      loadDepts();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Update failed";
      setError(msg);
    }
  };

  const handleDeleteDept = async (id: string) => {
    if (!workspaceId || !confirm("Delete this department?")) return;
    setError("");
    try {
      await deleteDepartment(workspaceId, id);
      loadDepts();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Delete failed";
      setError(msg);
    }
  };

  // --- Position handlers ---
  const handleCreatePos = async () => {
    if (!workspaceId) return;
    if (!newPos.title.trim()) { setError("Position title is required"); return; }
    setSavingPos(true);
    setError("");
    try {
      await createPosition(workspaceId, {
        title: newPos.title, level: newPos.level || undefined,
        department_id: newPos.department_id || undefined,
      });
      setNewPos({ title: "", level: "", department_id: "" });
      loadPositions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create position";
      setError(msg);
    } finally {
      setSavingPos(false);
    }
  };

  const handleDeletePos = async (id: string) => {
    if (!workspaceId || !confirm("Delete this position?")) return;
    try { await deletePosition(workspaceId, id); loadPositions(); } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  // --- Employee handlers ---
  const handleCreateEmp = async () => {
    if (!workspaceId) return;
    if (!newEmp.name.trim()) { setError("Employee name is required"); return; }
    setSavingEmp(true);
    setError("");
    try {
      await createEmployee(workspaceId, {
        name: newEmp.name, email: newEmp.email || undefined,
        department_id: newEmp.department_id || undefined,
        position_id: newEmp.position_id || undefined,
      });
      setNewEmp({ name: "", email: "", department_id: "", position_id: "" });
      loadEmployees();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create employee";
      setError(msg);
    } finally {
      setSavingEmp(false);
    }
  };

  const handleDeleteEmp = async (id: string) => {
    if (!workspaceId || !confirm("Delete this employee?")) return;
    try { await deleteEmployee(workspaceId, id); loadEmployees(); } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  if (!workspaceId) {
    return <div className="p-8 text-gray-400 text-center">Select a workspace first.</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <WorkspaceSelector />
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Organization Structure</h2>
        <p className="text-sm text-gray-500 mt-1">Manage departments, positions, and employees.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {(["dept", "pos", "emp"] as const).map((t) => (
          <button key={t} onClick={() => { setTab(t); setError(""); }}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? "bg-white text-gray-800 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "dept" ? "Departments" : t === "pos" ? "Positions" : "Employees"}
          </button>
        ))}
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* ─── Departments Tab ──────────────────────────── */}
      {tab === "dept" && (
        <Card>
          <CardHeader><CardTitle className="text-base">Departments</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input placeholder="Dept name" value={newDept.name}
                onChange={(e) => { setNewDept({ ...newDept, name: e.target.value }); setError(""); }}
                className="flex-1" />
              <Input placeholder="Type (e.g. Sales)" value={newDept.type}
                onChange={(e) => setNewDept({ ...newDept, type: e.target.value })}
                className="w-40" />
              <select value={newDept.parent_id} onChange={(e) => setNewDept({ ...newDept, parent_id: e.target.value })}
                className="w-48 text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white">
                <option value="">No Parent</option>
                {depts.map((d) => (<option key={d.id} value={d.id}>{d.name}</option>))}
              </select>
              <Button size="sm" onClick={handleCreateDept} disabled={savingDept}>
                <Plus size={14} className="mr-1" /> {savingDept ? "Adding..." : "Add"}
              </Button>
            </div>
            <div className="space-y-1">
              {depts.map((d) => (
                <div key={d.id} className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 group">
                  <span className="flex-1 text-sm font-medium">{d.name}</span>
                  <span className="text-xs text-gray-400">{d.type}</span>
                  {editDept[d.id] ? (
                    <>
                      <Input value={editDept[d.id].name}
                        onChange={(e) => setEditDept({ ...editDept, [d.id]: { ...editDept[d.id], name: e.target.value } })}
                        className="w-32 h-7 text-xs" />
                      <Button size="sm" variant="ghost" className="h-7 text-xs"
                        onClick={() => handleUpdateDept(d.id)}>Save</Button>
                    </>
                  ) : (
                    <Button size="sm" variant="ghost" className="h-7 text-xs opacity-0 group-hover:opacity-100"
                      onClick={() => setEditDept({ ...editDept, [d.id]: { name: d.name, type: d.type || "" } })}>
                      Edit
                    </Button>
                  )}
                  <button onClick={() => handleDeleteDept(d.id)}
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded">
                    <Trash2 size={12} className="text-red-400" />
                  </button>
                </div>
              ))}
              {depts.length === 0 && <p className="text-sm text-gray-400 py-4 text-center">No departments yet. Add your first one.</p>}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ─── Positions Tab ────────────────────────────── */}
      {tab === "pos" && (
        <Card>
          <CardHeader><CardTitle className="text-base">Positions</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input placeholder="Position title" value={newPos.title}
                onChange={(e) => { setNewPos({ ...newPos, title: e.target.value }); setError(""); }} className="flex-1" />
              <Input placeholder="Level" value={newPos.level}
                onChange={(e) => setNewPos({ ...newPos, level: e.target.value })} className="w-32" />
              <select value={newPos.department_id} onChange={(e) => setNewPos({ ...newPos, department_id: e.target.value })}
                className="w-48 text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white">
                <option value="">Any Department</option>
                {depts.map((d) => (<option key={d.id} value={d.id}>{d.name}</option>))}
              </select>
              <Button size="sm" onClick={handleCreatePos} disabled={savingPos}>
                <Plus size={14} className="mr-1" /> {savingPos ? "Adding..." : "Add"}
              </Button>
            </div>
            <div className="space-y-1">
              {positions.map((p) => (
                <div key={p.id} className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 group">
                  <span className="flex-1 text-sm font-medium">{p.title}</span>
                  <span className="text-xs text-gray-400">{p.level}</span>
                  <button onClick={() => handleDeletePos(p.id)}
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded">
                    <Trash2 size={12} className="text-red-400" />
                  </button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ─── Employees Tab ────────────────────────────── */}
      {tab === "emp" && (
        <Card>
          <CardHeader><CardTitle className="text-base">Employees</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input placeholder="Full name" value={newEmp.name}
                onChange={(e) => { setNewEmp({ ...newEmp, name: e.target.value }); setError(""); }} className="flex-1" />
              <Input placeholder="Email" value={newEmp.email}
                onChange={(e) => setNewEmp({ ...newEmp, email: e.target.value })} className="w-48" />
              <select value={newEmp.department_id} onChange={(e) => setNewEmp({ ...newEmp, department_id: e.target.value })}
                className="w-40 text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white">
                <option value="">Any Dept</option>
                {depts.map((d) => (<option key={d.id} value={d.id}>{d.name}</option>))}
              </select>
              <select value={newEmp.position_id} onChange={(e) => setNewEmp({ ...newEmp, position_id: e.target.value })}
                className="w-40 text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white">
                <option value="">Any Position</option>
                {positions.map((p) => (<option key={p.id} value={p.id}>{p.title}</option>))}
              </select>
              <Button size="sm" onClick={handleCreateEmp} disabled={savingEmp}>
                <Plus size={14} className="mr-1" /> {savingEmp ? "Adding..." : "Add"}
              </Button>
            </div>
            <div className="space-y-1">
              {employees.map((e) => (
                <div key={e.id} className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 group">
                  <span className="flex-1 text-sm font-medium">{e.name}</span>
                  <span className="text-xs text-gray-400">{e.email}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${e.status === "active" ? "bg-green-50 text-green-600" : "bg-gray-50 text-gray-500"}`}>
                    {e.status}
                  </span>
                  <button onClick={() => handleDeleteEmp(e.id)}
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded">
                    <Trash2 size={12} className="text-red-400" />
                  </button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
