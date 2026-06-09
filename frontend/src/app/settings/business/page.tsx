"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import {
  listProducts, createProduct, deleteProduct,
  listCustomers, createCustomer, deleteCustomer,
  listProcesses, createProcess, deleteProcess,
  type ProdData, type CustData, type ProcData,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2 } from "lucide-react";
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
                <span className="flex-1 text-sm font-medium">{p.name}</span>
                <span className="text-xs text-gray-400">{p.category}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${p.status === "active" ? "bg-green-50 text-green-600" : "bg-gray-50 text-gray-500"}`}>{p.status}</span>
                <button onClick={() => handleDelete("prod", p.id)} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded"><Trash2 size={12} className="text-red-400" /></button>
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
                <span className="flex-1 text-sm font-medium">{c.name}</span>
                <span className="text-xs text-gray-400">{c.market} · {c.type}</span>
                <span className="text-xs text-gray-400">{c.contact_email}</span>
                <button onClick={() => handleDelete("cust", c.id)} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded"><Trash2 size={12} className="text-red-400" /></button>
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
                <div className="flex-1">
                  <p className="text-sm font-medium">{p.name}</p>
                  {p.description && <p className="text-xs text-gray-400">{p.description}</p>}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${p.status === "active" ? "bg-green-50 text-green-600" : "bg-gray-50 text-gray-500"}`}>{p.status}</span>
                <button onClick={() => handleDelete("proc", p.id)} className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded"><Trash2 size={12} className="text-red-400" /></button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
