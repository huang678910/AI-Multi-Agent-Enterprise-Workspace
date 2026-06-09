"use client";
import { useEffect, useState } from "react";
import { useAuthStore, useWorkspaceStore, useChatStore } from "@/lib/stores";
import { listWorkspaces } from "@/lib/api-client";
import type { Workspace } from "@/types";
import { Building2 } from "lucide-react";

interface Props {
  label?: string;
}

export default function WorkspaceSelector({ label = "Current Workspace" }: Props) {
  const token = useAuthStore((s) => s.token);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);
  const setActiveWorkspace = useWorkspaceStore((s) => s.setActiveWorkspace);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const setStreaming = useChatStore((s) => s.setStreaming);

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    listWorkspaces()
      .then((d) => {
        setWorkspaces(d.workspaces);
        if (!activeWorkspaceId && d.workspaces.length > 0) {
          setActiveWorkspace(d.workspaces[0].id);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token]);

  const currentWs = workspaces.find((w) => w.id === activeWorkspaceId);

  const handleSwitch = (wsId: string) => {
    setActiveWorkspace(wsId);
    clearMessages();
    setStreaming(false);
  };

  return (
    <div className="flex items-center gap-3">
      <Building2 size={16} className="text-gray-400" />
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">{label}:</span>
        {loading ? (
          <span className="text-sm text-gray-400">Loading...</span>
        ) : workspaces.length === 0 ? (
          <span className="text-sm text-amber-600">No workspaces — create one in Chat first</span>
        ) : (
          <select
            value={activeWorkspaceId || ""}
            onChange={(e) => handleSwitch(e.target.value)}
            className="text-sm rounded-lg border border-gray-200 px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[180px]"
          >
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        )}
      </div>
      {currentWs && workspaces.length > 1 && (
        <span className="text-[10px] text-gray-400">
          ({workspaces.length} workspaces available)
        </span>
      )}
    </div>
  );
}
