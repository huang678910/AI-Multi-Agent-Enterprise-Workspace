"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Users, UserPlus, Trash2, Crown, User, Eye } from "lucide-react";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import {
  listWorkspaces,
  listMembers,
  addMember,
  updateMemberRole,
  removeMember,
  searchUsers,
} from "@/lib/api-client";
import type { Workspace } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Member {
  id: string;
  workspace_id: string;
  user_id: string;
  role: string;
  username: string;
  email: string;
  created_at: string;
}

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-amber-50 text-amber-700 border-amber-200",
  member: "bg-blue-50 text-blue-700 border-blue-200",
  viewer: "bg-gray-50 text-gray-600 border-gray-200",
};

export default function MembersPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const { activeWorkspaceId, setActiveWorkspace } = useWorkspaceStore();

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newUserId, setNewUserId] = useState("");
  const [newRole, setNewRole] = useState("member");
  const [error, setError] = useState("");
  // 用户搜索状态
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<{ id: string; email: string; username: string }[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedUser, setSelectedUser] = useState<{ id: string; email: string; username: string } | null>(null);

  // Auth guard
  useEffect(() => {
    if (!token) router.push("/login");
  }, [token, router]);

  // Load workspaces
  useEffect(() => {
    if (!token) return;
    listWorkspaces()
      .then((d) => {
        setWorkspaces(d.workspaces);
        if (!activeWorkspaceId && d.workspaces.length > 0) {
          setActiveWorkspace(d.workspaces[0].id);
        }
      })
      .catch(() => {});
  }, [token]);

  // Load members when workspace changes
  useEffect(() => {
    if (!activeWorkspaceId || !token) return;
    setLoading(true);
    setError("");
    listMembers(activeWorkspaceId)
      .then((d) => setMembers(d.members || []))
      .catch((err) => setError(err.response?.data?.detail || "Failed to load members"))
      .finally(() => setLoading(false));
  }, [activeWorkspaceId, token]);

  async function handleAddMember() {
    if (!activeWorkspaceId || !newUserId.trim()) return;
    try {
      setError("");
      const m = await addMember(activeWorkspaceId, newUserId.trim(), newRole);
      setMembers((prev) => [m, ...prev]);
      setNewUserId("");
      setSearchQuery("");
      setSelectedUser(null);
      setSearchResults([]);
      setShowAdd(false);
    } catch (err: unknown) {
      const msg = err instanceof Error && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "Failed to add member";
      setError(typeof msg === "string" ? msg : "Failed to add member");
    }
  }

  // 用户搜索（防抖）
  const handleUserSearch = useCallback(
    (() => {
      let timer: ReturnType<typeof setTimeout>;
      return (query: string) => {
        clearTimeout(timer);
        if (!query || query.length < 1) {
          setSearchResults([]);
          return;
        }
        setSearchQuery(query);
        timer = setTimeout(async () => {
          setSearching(true);
          try {
            const res = await searchUsers(query);
            setSearchResults(res.users || []);
          } catch {
            setSearchResults([]);
          } finally {
            setSearching(false);
          }
        }, 300);
      };
    })(),
    []
  );

  function handleSelectUser(user: { id: string; email: string; username: string }) {
    setNewUserId(user.id);
    setSelectedUser(user);
    setSearchQuery(`${user.username} (${user.email})`);
    setSearchResults([]);
  }

  async function handleRoleChange(memberId: string, role: string) {
    if (!activeWorkspaceId) return;
    try {
      setError("");
      const updated = await updateMemberRole(activeWorkspaceId, memberId, role);
      setMembers((prev) => prev.map((m) => (m.id === memberId ? updated : m)));
    } catch (err: unknown) {
      const msg = err instanceof Error && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "Failed to update role";
      setError(typeof msg === "string" ? msg : "Failed to update role");
    }
  }

  async function handleRemove(memberId: string, username: string) {
    if (!activeWorkspaceId) return;
    if (!confirm(`Remove "${username}" from this workspace?`)) return;
    try {
      setError("");
      await removeMember(activeWorkspaceId, memberId);
      setMembers((prev) => prev.filter((m) => m.id !== memberId));
    } catch (err: unknown) {
      const msg = err instanceof Error && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "Failed to remove member";
      setError(typeof msg === "string" ? msg : "Failed to remove member");
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-800">Members</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage workspace members and their permissions
          </p>
        </div>
        <Button
          onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-2"
          size="sm"
        >
          <UserPlus size={16} />
          Add Member
        </Button>
      </div>

      {/* Workspace Selector */}
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Workspace</label>
        <select
          value={activeWorkspaceId || ""}
          onChange={(e) => setActiveWorkspace(e.target.value)}
          className="mt-1 w-full max-w-xs text-sm rounded-lg border border-gray-200 px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {workspaces.map((w) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Add Member Form */}
      {showAdd && (
        <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Add New Member</h3>
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <label className="text-xs text-gray-400">Search by email or username</label>
              <Input
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setSelectedUser(null);
                  setNewUserId("");
                  handleUserSearch(e.target.value);
                }}
                placeholder="Type email or username to search..."
                className="h-9 text-sm mt-1"
                autoComplete="off"
              />
              {/* 搜索下拉 */}
              {searchResults.length > 0 && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {searchResults.map((user) => (
                    <button
                      key={user.id}
                      type="button"
                      onClick={() => handleSelectUser(user)}
                      className="w-full text-left px-3 py-2 hover:bg-blue-50 transition-colors border-b border-gray-50 last:border-0"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-500 flex-shrink-0">
                          {user.username?.charAt(0)?.toUpperCase() || "?"}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-700 truncate">{user.username}</p>
                          <p className="text-xs text-gray-400 truncate">{user.email}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {/* 搜索中 */}
              {searching && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs text-gray-400">
                  Searching...
                </div>
              )}
              {/* 已选用户 */}
              {selectedUser && (
                <p className="text-xs text-green-600 mt-1">
                  ✓ Selected: {selectedUser.username} ({selectedUser.email})
                </p>
              )}
            </div>
            <div>
              <label className="text-xs text-gray-400">Role</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="mt-1 text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="admin">Admin</option>
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <Button
              onClick={handleAddMember}
              size="sm"
              className="h-9"
              disabled={!selectedUser}
            >
              Add
            </Button>
          </div>
        </div>
      )}

      {/* Members List */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">
            <Users size={32} className="mx-auto mb-3 opacity-50" />
            <p className="text-sm">Loading members...</p>
          </div>
        ) : members.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <Users size={32} className="mx-auto mb-3 opacity-50" />
            <p className="text-sm">No members yet. Add your first member above.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase">User</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase">Role</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase">Joined</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-400 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-500">
                        {m.username?.charAt(0)?.toUpperCase() || "?"}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-700">{m.username || "Unknown"}</p>
                        <p className="text-xs text-gray-400">{m.email || "No email"}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={m.role}
                      onChange={(e) => handleRoleChange(m.id, e.target.value)}
                      className={`text-xs font-medium rounded-full px-2.5 py-1 border ${ROLE_COLORS[m.role] || ROLE_COLORS.member} cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500`}
                    >
                      <option value="admin">Admin</option>
                      <option value="member">Member</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {new Date(m.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleRemove(m.id, m.username)}
                      className="p-1.5 hover:bg-red-50 rounded transition-colors text-gray-400 hover:text-red-500"
                      title="Remove member"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Legend */}
      <div className="mt-6 flex gap-4 text-xs text-gray-400">
        <span className="flex items-center gap-1"><Crown size={12} className="text-amber-400" /> Admin — Full access</span>
        <span className="flex items-center gap-1"><User size={12} className="text-blue-400" /> Member — Read & write</span>
        <span className="flex items-center gap-1"><Eye size={12} className="text-gray-400" /> Viewer — Read only</span>
      </div>
    </div>
  );
}
