"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import { getCompany, upsertCompany } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import WorkspaceSelector from "@/components/layout/WorkspaceSelector";

export default function CompanySettingsPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [pageReady, setPageReady] = useState(false);

  const [form, setForm] = useState({
    name: "",
    industry: "",
    description: "",
    founded_year: "",
    employee_count: "0",
    markets: "",
    headquarters: "",
    website: "",
  });

  // Auth guard
  useEffect(() => {
    if (!token) { router.push("/login"); return; }
    setPageReady(true);
  }, [token, router]);

  // Clear form on workspace switch
  useEffect(() => {
    setForm({ name: "", industry: "", description: "", founded_year: "", employee_count: "0", markets: "", headquarters: "", website: "" });
    setSaved(false); setError("");
  }, [workspaceId]);

  // Load existing profile
  useEffect(() => {
    if (!workspaceId || !pageReady) return;
    getCompany(workspaceId)
      .then((data) => {
        if (data) {
          setForm({
            name: data.name || "",
            industry: data.industry || "",
            description: data.description || "",
            founded_year: data.founded_year?.toString() || "",
            employee_count: data.employee_count?.toString() || "0",
            markets: Array.isArray(data.markets) ? data.markets.join(", ") : "",
            headquarters: data.headquarters || "",
            website: data.website || "",
          });
        }
      })
      .catch(() => {
        // No profile yet — that's fine, form stays empty
      });
  }, [workspaceId, pageReady]);

  const update = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((f) => ({ ...f, [k]: e.target.value }));
    setSaved(false);
    setError("");
  };

  const handleSave = async () => {
    if (!workspaceId) {
      setError("No workspace selected");
      return;
    }
    if (!form.name.trim()) {
      setError("Company name is required");
      return;
    }
    setSaving(true);
    setError("");
    try {
      console.log("[Company] Saving:", form.name);
      await upsertCompany(workspaceId, {
        name: form.name,
        industry: form.industry || undefined,
        description: form.description || undefined,
        founded_year: form.founded_year ? parseInt(form.founded_year) : undefined,
        employee_count: form.employee_count ? parseInt(form.employee_count) : 0,
        markets: form.markets ? form.markets.split(",").map((s) => s.trim()).filter(Boolean) : [],
        headquarters: form.headquarters || undefined,
        website: form.website || undefined,
        extra_data: {},
      });
      console.log("[Company] Saved OK");
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Save failed";
      console.error("[Company] Save error:", err);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  if (!workspaceId) {
    return <div className="p-8 text-gray-400 text-center">Select a workspace to configure company profile.</div>;
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <WorkspaceSelector />
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Company Profile</h2>
        <p className="text-sm text-gray-500 mt-1">Configure your enterprise profile for AI-powered insights.</p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Basic Information</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Company Name *</label>
              <Input value={form.name} onChange={update("name")} placeholder="e.g. Acme Corp" className="mt-1" />
            </div>
            <div>
              <label className="text-sm font-medium">Industry</label>
              <Input value={form.industry} onChange={update("industry")} placeholder="e.g. E-commerce" className="mt-1" />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium">Description</label>
            <textarea
              value={form.description}
              onChange={update("description")}
              placeholder="Brief description of your company..."
              rows={3}
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium">Founded Year</label>
              <Input value={form.founded_year} onChange={update("founded_year")} placeholder="e.g. 2020" className="mt-1" />
            </div>
            <div>
              <label className="text-sm font-medium">Employees</label>
              <Input value={form.employee_count} onChange={update("employee_count")} type="number" className="mt-1" />
            </div>
            <div>
              <label className="text-sm font-medium">Headquarters</label>
              <Input value={form.headquarters} onChange={update("headquarters")} placeholder="e.g. Shanghai" className="mt-1" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Market & Online Presence</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Target Markets (comma-separated)</label>
            <Input value={form.markets} onChange={update("markets")} placeholder="e.g. US, Europe, Japan" className="mt-1" />
          </div>
          <div>
            <label className="text-sm font-medium">Website</label>
            <Input value={form.website} onChange={update("website")} placeholder="e.g. https://example.com" className="mt-1" />
          </div>
        </CardContent>
      </Card>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="flex items-center gap-4">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Profile"}
        </Button>
        {saved && <span className="text-sm text-green-600 font-medium">Profile saved successfully!</span>}
      </div>
    </div>
  );
}
