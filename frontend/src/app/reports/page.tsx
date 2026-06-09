"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Download, Trash2 } from "lucide-react";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import { listWorkspaces, deleteReport, listMembers } from "@/lib/api-client";
import type { Workspace } from "@/types";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";

interface Report {
  id: string;
  workspace_id: string;
  title: string;
  content: string;
  format: string;
  file_path: string | null;
  created_at: string;
}

export default function ReportsPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const currentUser = useAuthStore((s) => s.user);
  const { activeWorkspaceId, setActiveWorkspace } = useWorkspaceStore();
  const queryClient = useQueryClient();
  const [isAdmin, setIsAdmin] = useState(false);

  const dlBase = (report: { workspace_id: string; id: string }) =>
    `${api.defaults.baseURL}/api/v1/workspaces/${report.workspace_id}/reports/${report.id}/download`;

  async function handleDeleteReport(reportId: string, title: string) {
    if (!activeWorkspaceId) { alert("No workspace selected"); return; }
    if (!confirm(`Delete report "${title}"?`)) return;
    try {
      await deleteReport(activeWorkspaceId, reportId);
      queryClient.invalidateQueries({ queryKey: ["reports", activeWorkspaceId] });
    } catch (err: unknown) {
      alert("Failed to delete report: " + ((err as Error).message || "Unknown error"));
    }
  }

  useEffect(() => { if (!token) router.push("/login"); }, [token, router]);

  const { data: wsData } = useQuery({
    queryKey: ["workspaces"],
    queryFn: listWorkspaces,
    enabled: !!token,
  });
  const workspaces: Workspace[] = wsData?.workspaces || [];

  useEffect(() => {
    if (!activeWorkspaceId && workspaces.length > 0) {
      setActiveWorkspace(workspaces[0].id);
    }
  }, [workspaces, activeWorkspaceId, setActiveWorkspace]);

  const { data: reportsData, isLoading } = useQuery({
    queryKey: ["reports", activeWorkspaceId],
    queryFn: () => api.get(`/api/v1/workspaces/${activeWorkspaceId}/reports`).then(r => r.data),
    enabled: !!activeWorkspaceId && !!token,
  });
  const reports: Report[] = reportsData?.reports || [];

  useEffect(() => {
    if (!activeWorkspaceId || !token) return;
    listMembers(activeWorkspaceId)
      .then((d: { members: { user_id: string; role: string }[] }) => {
        if (currentUser?.id) {
          const me = d.members.find((m: { user_id: string; role: string }) => m.user_id === currentUser.id);
          setIsAdmin(me?.role === "admin");
        }
      })
      .catch(() => setIsAdmin(false));
  }, [activeWorkspaceId, token, currentUser]);

  const formatLabel = (fmt: string) => {
    switch (fmt) { case "pdf": return "PDF"; case "docx": return "DOCX"; default: return "Markdown"; }
  };
  const formatColor = (fmt: string) => {
    switch (fmt) { case "pdf": return "bg-red-50 text-red-600"; case "docx": return "bg-blue-50 text-blue-600"; default: return "bg-gray-50 text-gray-600"; }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-800">Reports</h1>
          <p className="text-sm text-gray-500 mt-1">Generated AI reports and documents</p>
        </div>
      </div>

      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Workspace</label>
        <select value={activeWorkspaceId || ""} onChange={(e) => setActiveWorkspace(e.target.value)}
          className="mt-1 w-full max-w-xs text-sm rounded-lg border border-gray-200 px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500">
          {workspaces.map((w) => (<option key={w.id} value={w.id}>{w.name}</option>))}
        </select>
      </div>

      {isLoading ? (
        <div className="text-center text-gray-400 py-12">
          <FileText size={32} className="mx-auto mb-3 opacity-50" />
          <p className="text-sm">Loading reports...</p>
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center text-gray-400 py-12 bg-white rounded-lg border border-gray-200">
          <FileText size={32} className="mx-auto mb-3 opacity-50" />
          <p className="text-sm">No reports yet. Generate reports via the Chat or API.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {reports.map((r) => (
            <div key={r.id} className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText size={16} className="text-gray-400 flex-shrink-0" />
                    <h3 className="text-sm font-medium text-gray-800 truncate">{r.title}</h3>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${formatColor(r.format)}`}>{formatLabel(r.format)}</span>
                  </div>
                  <p className="text-xs text-gray-400 mb-3">{new Date(r.created_at).toLocaleString()} &middot; {r.content.length.toLocaleString()} chars</p>
                  <div className="text-xs text-gray-500 line-clamp-2">{r.content.substring(0, 200)}...</div>
                </div>
                <div className="ml-4 flex-shrink-0 flex items-center gap-1">
                  <a href={`${dlBase(r)}?token=${token}`} target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" size="sm" className="flex items-center gap-1 text-xs"><Download size={12} /> MD</Button>
                  </a>
                  <a href={`${dlBase(r)}?format=pdf&token=${token}`} target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" size="sm" className="flex items-center gap-1 text-xs text-red-500 border-red-200 hover:bg-red-50"><Download size={12} /> PDF</Button>
                  </a>
                  <a href={`${dlBase(r)}?format=docx&token=${token}`} target="_blank" rel="noopener noreferrer">
                    <Button variant="outline" size="sm" className="flex items-center gap-1 text-xs text-blue-500 border-blue-200 hover:bg-blue-50"><Download size={12} /> DOCX</Button>
                  </a>
                  {isAdmin && (
                    <button onClick={() => handleDeleteReport(r.id, r.title)}
                      className="p-1.5 hover:bg-red-50 rounded transition-colors text-gray-400 hover:text-red-500"
                      title="Delete report (Admin only)">
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
