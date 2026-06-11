"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import {
  listProducts, createProduct, updateProduct, deleteProduct,
  listCustomers, createCustomer, updateCustomer, deleteCustomer,
  listProcesses, createProcess, updateProcess, deleteProcess,
  type ProdData, type CustData, type ProcData,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2, Edit3, X } from "lucide-react";
import WorkspaceSelector from "@/components/layout/WorkspaceSelector";

export default function BusinessSettingsPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const [tab, setTab] = useState<"prod" | "cust" | "proc">("prod");
  const [error, setError] = useState("");

  const [products, setProducts] = useState<ProdData[]>([]);
  const [newProd, setNewProd] = useState({ name: "", category: "", target_market: "" });
  const [savingProd, setSavingProd] = useState(false);

  const [customers, setCustomers] = useState<CustData[]>([]);
  const [newCust, setNewCust] = useState({ name: "", market: "", type: "", contact_email: "" });
  const [savingCust, setSavingCust] = useState(false);

  const [processes, setProcesses] = useState<ProcData[]>([]);
  const [newProc, setNewProc] = useState({ name: "", description: "" });
  const [savingProc, setSavingProc] = useState(false);

  // Inline edit state
  const [editProd, setEditProd] = useState<Record<string, { name: string; category: string; target_market: string }>>({});
  const [editCust, setEditCust] = useState<Record<string, { name: string; market: string; type: string; contact_email: string }>>({});
  const [editProc, setEditProc] = useState<Record<string, { name: string; description: string }>>({});

  useEffect(() => { if (!token) router.push("/login"); }, [token, router]);

  // Clear data + error on workspace switch
  useEffect(() => {
    setProducts([]); setCustomers([]); setProcesses([]);
    setError("");
  }, [workspaceId]);

  const loadAll = useCallback(async () => {
    if (!workspaceId) return;
    try { setProducts(await listProducts(workspaceId)); } catch {}
    try { setCustomers(await listCustomers(workspaceId)); } catch {}
    try { setProcesses(await listProcesses(workspaceId)); } catch {}
  }, [workspaceId]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleCreateProd = async () => {
    if (!workspaceId) return;
    if (!newProd.name.trim()) { setError("Product name is required"); return; }
    setSavingProd(true); setError("");
    try {
      await createProduct(workspaceId, {
        name: newProd.name, category: newProd.category || undefined,
        target_market: newProd.target_market ? newProd.target_market.split(",").map(s => s.trim()).filter(Boolean) : [],
      });
      setNewProd({ name: "", category: "", target_market: "" });
      loadAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create product";
      setError(msg);
    } finally { setSavingProd(false); }
  };

  const handleCreateCust = async () => {
    if (!workspaceId) return;
    if (!newCust.name.trim()) { setError("Customer name is required"); return; }
    setSavingCust(true); setError("");
    try {
      await createCustomer(workspaceId, {
        name: newCust.name, market: newCust.market || undefined,
        type: newCust.type || undefined, contact_email: newCust.contact_email || undefined,
      });
      setNewCust({ name: "", market: "", type: "", contact_email: "" });
      loadAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create customer";
      setError(msg);
    } finally { setSavingCust(false); }
  };

  const handleCreateProc = async () => {
    if (!workspaceId) return;
    if (!newProc.name.trim()) { setError("Process name is required"); return; }
    setSavingProc(true); setError("");
    try {
      await createProcess(workspaceId, {
        name: newProc.name, description: newProc.description || undefined,
      });
      setNewProc({ name: "", description: "" });
      loadAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create process";
      setError(msg);
    } finally { setSavingProc(false); }
  };

  const handleDelete = async (type: string, id: string) => {
    if (!workspaceId || !confirm(`Delete this ${type}?`)) return;
    setError("");
    try {
      if (type === "prod") await deleteProduct(workspaceId, id);
      else if (type === "cust") await deleteCustomer(workspaceId, id);
      else if (type === "proc") await deleteProcess(workspaceId, id);
      loadAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Delete failed";
      setError(msg);
    }
  };

  // ─── Inline Update Handlers ──────────────────────────

  const handleUpdateProd = async (id: string) => {
    if (!workspaceId) return;
    const e = editProd[id];
    if (!e || !e.name.trim()) return;
    setError("");
    try {
      await updateProduct(workspaceId, id, {
        name: e.name, category: e.category || undefined,
        target_market: e.target_market ? e.target_market.split(",").map(s => s.trim()).filter(Boolean) : [],
      });
      const next = { ...editProd }; delete next[id]; setEditProd(next);
      loadAll();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  const handleUpdateCust = async (id: string) => {
    if (!workspaceId) return;
    const e = editCust[id];
    if (!e || !e.name.trim()) return;
    setError("");
    try {
      await updateCustomer(workspaceId, id, {
        name: e.name, market: e.market || undefined,
        type: e.type || undefined, contact_email: e.contact_email || undefined,
      });
      const next = { ...editCust }; delete next[id]; setEditCust(next);
      loadAll();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  const handleUpdateProc = async (id: string) => {
    if (!workspaceId) return;
    const e = editProc[id];
    if (!e || !e.name.trim()) return;
    setError("");
    try {
      await updateProcess(workspaceId, id, {
        name: e.name, description: e.description || undefined,
      });
      const next = { ...editProc }; delete next[id]; setEditProc(next);
      loadAll();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  if (!workspaceId) return <div className="p-8 text-gray-400 text-center">Select a workspace first.</div>;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <WorkspaceSelector />
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Business Management</h2>
        <p className="text-sm text-gray-500 mt-1">Manage products, customers, and business processes.</p>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {(["prod", "cust", "proc"] as const).map((t) => (
          <button key={t} onClick={() => { setTab(t); setError(""); }}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? "bg-white text-gray-800 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}>
            {t === "prod" ? "Products" : t === "cust" ? "Customers" : "Processes"}
          </button>
        ))}
      </div>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>}

      {/* Products */}
      {tab === "prod" && (
        <Card>
          <CardHeader><CardTitle className="text-base">Products & Services</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input placeholder="Product name" value={newProd.name} onChange={(e) => { setNewProd({ ...newProd, name: e.target.value }); setError(""); }} className="flex-1" />
              <Input placeholder="Category" value={newProd.category} onChange={(e) => setNewProd({ ...newProd, category: e.target.value })} className="w-40" />
              <Input placeholder="Markets (comma-sep)" value={newProd.target_market} onChange={(e) => setNewProd({ ...newProd, target_market: e.target.value })} className="w-48" />
              <Button size="sm" onClick={handleCreateProd} disabled={savingProd}><Plus size={14} className="mr-1" /> {savingProd ? "Adding..." : "Add"}</Button>
            </div>
            {products.map((p) => (
              <div key={p.id} className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 group">
                {editProd[p.id] ? (
                  <>
                    <Input value={editProd[p.id].name} onChange={(e) => setEditProd({ ...editProd, [p.id]: { ...editProd[p.id], name: e.target.value } })} className="flex-1 h-7 text-xs" />
                    <Input value={editProd[p.id].category} onChange={(e) => setEditProd({ ...editProd, [p.id]: { ...editProd[p.id], category: e.target.value } })} className="w-32 h-7 text-xs" placeholder="Category" />
                    <Input value={editProd[p.id].target_market} onChange={(e) => setEditProd({ ...editProd, [p.id]: { ...editProd[p.id], target_market: e.target.value } })} className="w-40 h-7 text-xs" placeholder="Markets" />
                    <Button size="sm" variant="ghost" className="h-7 text-xs px-2" onClick={() => handleUpdateProd(p.id)}>Save</Button>
                    <button onClick={() => { const n = { ...editProd }; delete n[p.id]; setEditProd(n); }} className="p-0.5 hover:bg-gray-200 rounded"><X size={12} /></button>
                  </>
                ) : (
                  <>
                    <span className="flex-1 text-sm font-medium">{p.name}</span>
                    <span className="text-xs text-gray-400">{p.category}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${p.status === "active" ? "bg-green-50 text-green-600" : "bg-gray-50 text-gray-500"}`}>{p.status}</span>
                    <button onClick={() => setEditProd({ ...editProd, [p.id]: { name: p.name, category: p.category || "", target_market: (p.target_market || []).join(", ") } })} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-blue-50 rounded"><Edit3 size={12} className="text-blue-400" /></button>
                    <button onClick={() => handleDelete("prod", p.id)} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded"><Trash2 size={12} className="text-red-400" /></button>
                  </>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Customers */}
      {tab === "cust" && (
        <Card>
          <CardHeader><CardTitle className="text-base">Customers</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input placeholder="Customer name" value={newCust.name} onChange={(e) => { setNewCust({ ...newCust, name: e.target.value }); setError(""); }} className="flex-1" />
              <Input placeholder="Market" value={newCust.market} onChange={(e) => setNewCust({ ...newCust, market: e.target.value })} className="w-32" />
              <Input placeholder="Type" value={newCust.type} onChange={(e) => setNewCust({ ...newCust, type: e.target.value })} className="w-32" />
              <Input placeholder="Email" value={newCust.contact_email} onChange={(e) => setNewCust({ ...newCust, contact_email: e.target.value })} className="w-48" />
              <Button size="sm" onClick={handleCreateCust} disabled={savingCust}><Plus size={14} className="mr-1" /> {savingCust ? "Adding..." : "Add"}</Button>
            </div>
            {customers.map((c) => (
              <div key={c.id} className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 group">
                {editCust[c.id] ? (
                  <>
                    <Input value={editCust[c.id].name} onChange={(e) => setEditCust({ ...editCust, [c.id]: { ...editCust[c.id], name: e.target.value } })} className="flex-1 h-7 text-xs" />
                    <Input value={editCust[c.id].market} onChange={(e) => setEditCust({ ...editCust, [c.id]: { ...editCust[c.id], market: e.target.value } })} className="w-24 h-7 text-xs" placeholder="Market" />
                    <Input value={editCust[c.id].type} onChange={(e) => setEditCust({ ...editCust, [c.id]: { ...editCust[c.id], type: e.target.value } })} className="w-24 h-7 text-xs" placeholder="Type" />
                    <Input value={editCust[c.id].contact_email} onChange={(e) => setEditCust({ ...editCust, [c.id]: { ...editCust[c.id], contact_email: e.target.value } })} className="w-36 h-7 text-xs" placeholder="Email" />
                    <Button size="sm" variant="ghost" className="h-7 text-xs px-2" onClick={() => handleUpdateCust(c.id)}>Save</Button>
                    <button onClick={() => { const n = { ...editCust }; delete n[c.id]; setEditCust(n); }} className="p-0.5 hover:bg-gray-200 rounded"><X size={12} /></button>
                  </>
                ) : (
                  <>
                    <span className="flex-1 text-sm font-medium">{c.name}</span>
                    <span className="text-xs text-gray-400">{c.market} · {c.type}</span>
                    <span className="text-xs text-gray-400">{c.contact_email}</span>
                    <button onClick={() => setEditCust({ ...editCust, [c.id]: { name: c.name, market: c.market || "", type: c.type || "", contact_email: c.contact_email || "" } })} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-blue-50 rounded"><Edit3 size={12} className="text-blue-400" /></button>
                    <button onClick={() => handleDelete("cust", c.id)} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded"><Trash2 size={12} className="text-red-400" /></button>
                  </>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Processes */}
      {tab === "proc" && (
        <Card>
          <CardHeader><CardTitle className="text-base">Business Processes</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input placeholder="Process name" value={newProc.name} onChange={(e) => { setNewProc({ ...newProc, name: e.target.value }); setError(""); }} className="flex-1" />
              <Input placeholder="Description" value={newProc.description} onChange={(e) => setNewProc({ ...newProc, description: e.target.value })} className="flex-1" />
              <Button size="sm" onClick={handleCreateProc} disabled={savingProc}><Plus size={14} className="mr-1" /> {savingProc ? "Adding..." : "Add"}</Button>
            </div>
            {processes.map((p) => (
              <div key={p.id} className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 group">
                {editProc[p.id] ? (
                  <>
                    <Input value={editProc[p.id].name} onChange={(e) => setEditProc({ ...editProc, [p.id]: { ...editProc[p.id], name: e.target.value } })} className="flex-1 h-7 text-xs" placeholder="Name" />
                    <Input value={editProc[p.id].description} onChange={(e) => setEditProc({ ...editProc, [p.id]: { ...editProc[p.id], description: e.target.value } })} className="flex-1 h-7 text-xs" placeholder="Description" />
                    <Button size="sm" variant="ghost" className="h-7 text-xs px-2" onClick={() => handleUpdateProc(p.id)}>Save</Button>
                    <button onClick={() => { const n = { ...editProc }; delete n[p.id]; setEditProc(n); }} className="p-0.5 hover:bg-gray-200 rounded"><X size={12} /></button>
                  </>
                ) : (
                  <>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{p.name}</p>
                      {p.description && <p className="text-xs text-gray-400">{p.description}</p>}
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${p.status === "active" ? "bg-green-50 text-green-600" : "bg-gray-50 text-gray-500"}`}>{p.status}</span>
                    <button onClick={() => setEditProc({ ...editProc, [p.id]: { name: p.name, description: p.description || "" } })} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-blue-50 rounded"><Edit3 size={12} className="text-blue-400" /></button>
                    <button onClick={() => handleDelete("proc", p.id)} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded"><Trash2 size={12} className="text-red-400" /></button>
                  </>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
