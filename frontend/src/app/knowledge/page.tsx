"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import { listWorkspaces, listDocuments, searchKnowledge } from "@/lib/api-client";
import type { Workspace, Document, SearchResult } from "@/types";
import KnowledgeStats from "@/components/knowledge/KnowledgeStats";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Search, FileText, GitFork, Mic, Upload, CheckCircle, XCircle, Loader2, BookOpen, ListTodo, FileBox } from "lucide-react";
import WorkspaceSelector from "@/components/layout/WorkspaceSelector";
import api from "@/lib/api";

type TabType = "search" | "github" | "notion" | "jira" | "confluence" | "audio";

const CONNECTOR_CONFIG: Record<string, { icon: typeof GitFork; label: string; fields: { key: string; placeholder: string; type?: string }[]; docs: string }> = {
  github: {
    icon: GitFork, label: "GitHub",
    fields: [
      { key: "token", placeholder: "GitHub Token (ghp_...)", type: "password" },
      { key: "owner", placeholder: "Owner (e.g. facebook)" },
      { key: "repo", placeholder: "Repo (e.g. react)" },
    ],
    docs: "Needs repo scope. Get token at github.com/settings/tokens",
  },
  notion: {
    icon: BookOpen, label: "Notion",
    fields: [
      { key: "api_key", placeholder: "Notion API Key (secret_...)", type: "password" },
      { key: "database_id", placeholder: "Database ID (optional)" },
    ],
    docs: "Create an integration at notion.so/my-integrations. Connect pages to the integration.",
  },
  jira: {
    icon: ListTodo, label: "Jira",
    fields: [
      { key: "email", placeholder: "Email (you@company.com)" },
      { key: "api_token", placeholder: "API Token", type: "password" },
      { key: "domain", placeholder: "Domain (e.g. company.atlassian.net)" },
      { key: "project_key", placeholder: "Project Key (e.g. PROJ)" },
    ],
    docs: "Generate API token at id.atlassian.com/manage-profile/security/api-tokens",
  },
  confluence: {
    icon: FileBox, label: "Confluence",
    fields: [
      { key: "email", placeholder: "Email (you@company.com)" },
      { key: "api_token", placeholder: "API Token", type: "password" },
      { key: "domain", placeholder: "Domain (e.g. company.atlassian.net)" },
      { key: "space_key", placeholder: "Space Key (e.g. TEAM)" },
    ],
    docs: "Same API token as Jira. Space key is found in the Confluence URL: /wiki/spaces/KEY/",
  },
};

const CONNECTOR_ICONS: Record<string, typeof GitFork> = {
  github: GitFork, notion: BookOpen, jira: ListTodo, confluence: FileBox,
};

export default function KnowledgePage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const { activeWorkspaceId, setActiveWorkspace } = useWorkspaceStore();

  const [tab, setTab] = useState<TabType>("search");
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  // Generic connector state
  const [connForms, setConnForms] = useState<Record<string, Record<string, string>>>({});
  const [connSyncing, setConnSyncing] = useState<Record<string, boolean>>({});
  const [connResults, setConnResults] = useState<Record<string, { ok: boolean; msg: string } | null>>({});
  const [connections, setConnections] = useState<{ source_type: string; doc_count: number; last_synced: string }[]>([]);

  // Audio state
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioLang, setAudioLang] = useState("zh");
  const [audioTranscribing, setAudioTranscribing] = useState(false);
  const [audioResult, setAudioResult] = useState<{ ok: boolean; msg: string; transcript?: string; docId?: string } | null>(null);

  useEffect(() => {
    if (!token) { router.push("/login"); return; }
    listWorkspaces().then((d) => {
      setWorkspaces(d.workspaces);
      if (!activeWorkspaceId && d.workspaces.length > 0) {
        setActiveWorkspace(d.workspaces[0].id);
      }
    }).catch(() => {});
  }, [token]);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    listDocuments(activeWorkspaceId).then((d) => setDocuments(d.documents)).catch(() => {});
    loadConnections();
  }, [activeWorkspaceId]);

  async function loadConnections() {
    if (!activeWorkspaceId) return;
    try {
      const res = await api.get(`/api/v1/workspaces/${activeWorkspaceId}/knowledge/connections`);
      setConnections(res.data.connections || []);
    } catch {}
  }

  async function handleSearch() {
    if (!activeWorkspaceId || !searchQuery.trim()) return;
    setSearching(true);
    try {
      const result = await searchKnowledge(activeWorkspaceId, searchQuery, 5);
      setSearchResults(result.results);
    } catch (err) { console.error("Search failed:", err); }
    finally { setSearching(false); }
  }

  function getConnForm(connType: string) {
    return connForms[connType] || {};
  }

  function setConnForm(connType: string, key: string, value: string) {
    setConnForms((prev) => ({
      ...prev,
      [connType]: { ...(prev[connType] || {}), [key]: value },
    }));
  }

  async function handleConnectorSync(connType: string) {
    if (!activeWorkspaceId) return;
    const config = CONNECTOR_CONFIG[connType];
    if (!config) return;

    const form = getConnForm(connType);
    const missing = config.fields.filter((f) => !form[f.key]?.trim());
    if (missing.length > 0) {
      setConnResults((p) => ({ ...p, [connType]: { ok: false, msg: `Missing: ${missing.map((f) => f.placeholder).join(", ")}` } }));
      return;
    }

    setConnSyncing((p) => ({ ...p, [connType]: true }));
    setConnResults((p) => ({ ...p, [connType]: null }));
    try {
      const res = await api.post(`/api/v1/workspaces/${activeWorkspaceId}/knowledge/connect/${connType}`, form);
      const data = res.data;
      if (data.error) {
        setConnResults((p) => ({ ...p, [connType]: { ok: false, msg: data.error } }));
      } else {
        setConnResults((p) => ({ ...p, [connType]: { ok: true, msg: data.message || `Synced ${data.synced} items` } }));
        setConnForms((prev) => { const n = { ...prev }; delete n[connType]; return n; });
        loadConnections();
        listDocuments(activeWorkspaceId).then((d) => setDocuments(d.documents)).catch(() => {});
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setConnResults((p) => ({ ...p, [connType]: { ok: false, msg: detail || "Connection failed" } }));
    } finally {
      setConnSyncing((p) => ({ ...p, [connType]: false }));
    }
  }

  async function handleAudioUpload() {
    if (!activeWorkspaceId || !audioFile) return;
    setAudioTranscribing(true);
    setAudioResult(null);
    try {
      const formData = new FormData();
      formData.append("file", audioFile);
      formData.append("language", audioLang);
      const res = await api.post(`/api/v1/workspaces/${activeWorkspaceId}/knowledge/transcribe`, formData);
      const data = res.data;
      if (data.error) {
        setAudioResult({ ok: false, msg: data.error });
      } else {
        setAudioResult({ ok: true, msg: `Transcribed ${data.full_length} characters`, transcript: data.transcript, docId: data.document_id });
        setAudioFile(null);
        listDocuments(activeWorkspaceId).then((d) => setDocuments(d.documents)).catch(() => {});
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAudioResult({ ok: false, msg: detail || "Transcription failed" });
    } finally { setAudioTranscribing(false); }
  }

  const totalChunks = documents.reduce((sum, d) => sum + d.chunk_count, 0);
  const currentWs = workspaces.find((w) => w.id === activeWorkspaceId);

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Knowledge Hub</h1>
        <p className="text-sm text-gray-500 mt-1">
          Semantic search, external connections, and audio transcription in{" "}
          <span className="font-medium text-gray-700">{currentWs?.name || "..."}</span>
        </p>
      </div>

      <div className="mb-6">
        <WorkspaceSelector />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit mb-6 flex-wrap">
        {(["search", "github", "notion", "jira", "confluence", "audio"] as TabType[]).map((t) => {
          const cfg = CONNECTOR_CONFIG[t];
          const Icon = t === "search" ? Search : t === "audio" ? Mic : cfg?.icon || GitFork;
          const label = t === "search" ? "Search" : t === "audio" ? "Audio" : cfg?.label || t;
          return (
            <button key={t} onClick={() => setTab(t)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === t ? "bg-white text-gray-800 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}>
              <Icon size={14} />
              {label}
            </button>
          );
        })}
      </div>

      {/* Stats */}
      <div className="mb-6">
        <KnowledgeStats documentCount={documents.length} totalChunks={totalChunks} />
      </div>

      {/* ─── Search Tab ───────────────────────────────── */}
      {tab === "search" && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Semantic Search</h3>
            <div className="flex gap-2">
              <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search your knowledge base..."
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="flex-1" />
              <Button onClick={handleSearch} disabled={searching}>
                <Search size={16} className="mr-1" /> {searching ? "Searching..." : "Search"}
              </Button>
            </div>
            {searchResults && (
              <div className="mt-4 space-y-3">
                <p className="text-xs text-gray-400">{searchResults.length} result{searchResults.length !== 1 ? "s" : ""}</p>
                {searchResults.map((r, i) => (
                  <div key={i} className="p-4 rounded-lg border border-gray-100 bg-gray-50">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText size={14} className="text-gray-400" />
                      <span className="text-xs font-medium text-gray-600">{r.filename}</span>
                      <span className="text-[10px] text-gray-400">{(r.similarity * 100).toFixed(1)}%</span>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed line-clamp-4">{r.content}</p>
                  </div>
                ))}
                {searchResults.length === 0 && <p className="text-sm text-gray-400 text-center py-4">No results found.</p>}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ─── Connector Tabs (github/notion/jira/confluence) ── */}
      {(["github", "notion", "jira", "confluence"] as TabType[]).includes(tab) && tab !== "search" && tab !== "audio" && (
        <div className="space-y-6">
          {(() => {
            const cfg = CONNECTOR_CONFIG[tab];
            if (!cfg) return null;
            const Icon = cfg.icon || GitFork;
            const form = getConnForm(tab);
            const syncing = connSyncing[tab] || false;
            const result = connResults[tab] || null;

            return (
              <Card>
                <CardContent className="p-6">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                    <Icon size={16} /> Connect {cfg.label}
                  </h3>
                  <p className="text-xs text-gray-500 mb-4">{cfg.docs}</p>
                  <div className="space-y-3">
                    {cfg.fields.map((field) => (
                      <div key={field.key}>
                        <Input
                          placeholder={field.placeholder}
                          value={form[field.key] || ""}
                          onChange={(e) => { setConnForm(tab, field.key, e.target.value); setConnResults((p) => ({ ...p, [tab]: null })); }}
                          type={field.type || "text"}
                          className="w-full"
                        />
                      </div>
                    ))}
                    <Button onClick={() => handleConnectorSync(tab)} disabled={syncing} className="w-full sm:w-auto">
                      {syncing ? <><Loader2 size={14} className="mr-1 animate-spin" /> Syncing...</> : <><Upload size={14} className="mr-1" /> Sync {cfg.label}</>}
                    </Button>
                  </div>
                  {result && (
                    <div className={`mt-4 p-3 rounded-lg text-sm flex items-center gap-2 ${
                      result.ok ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"
                    }`}>
                      {result.ok ? <CheckCircle size={16} /> : <XCircle size={16} />}
                      {result.msg}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })()}

          {/* Connections List */}
          <Card>
            <CardContent className="p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Active Connections</h3>
              {connections.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">No external connections yet. Connect a data source above.</p>
              ) : (
                <div className="space-y-2">
                  {connections.map((c) => {
                    const CIcon = CONNECTOR_ICONS[c.source_type] || GitFork;
                    return (
                      <div key={c.source_type} className="flex items-center justify-between p-3 rounded-lg border border-gray-100 bg-gray-50">
                        <div className="flex items-center gap-2">
                          <CIcon size={14} className="text-gray-500" />
                          <span className="text-sm font-medium text-gray-700">{c.source_type}</span>
                          <span className="text-xs text-gray-400">{c.doc_count} document{c.doc_count !== 1 ? "s" : ""}</span>
                        </div>
                        <span className="text-xs text-gray-400">
                          Last synced: {c.last_synced ? new Date(c.last_synced).toLocaleString() : "N/A"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ─── Audio Tab ─────────────────────────────────── */}
      {tab === "audio" && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <Mic size={16} /> Audio Transcription
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Upload a meeting recording (.mp3, .wav, .m4a, .ogg) and transcribe it to text.<br />
              The transcript will be automatically added to your knowledge base for RAG search.<br />
              <span className="text-amber-600 font-medium">Note: First use downloads Whisper small model (~244MB). Max file size: 25MB.</span>
            </p>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 text-sm">
                  <Upload size={14} />
                  {audioFile ? audioFile.name : "Choose audio file..."}
                  <input type="file" accept=".mp3,.wav,.m4a,.ogg,.webm,.flac" className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) { setAudioFile(f); setAudioResult(null); } }} />
                </label>
                <select value={audioLang} onChange={(e) => setAudioLang(e.target.value)}
                  className="text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white">
                  <option value="zh">中文</option>
                  <option value="en">English</option>
                  <option value="ja">日本語</option>
                  <option value="auto">Auto Detect</option>
                </select>
                <Button onClick={handleAudioUpload} disabled={audioTranscribing || !audioFile}>
                  {audioTranscribing ? <><Loader2 size={14} className="mr-1 animate-spin" /> Transcribing...</> : <><Mic size={14} className="mr-1" /> Transcribe</>}
                </Button>
              </div>
              {audioFile && <p className="text-xs text-gray-400">{(audioFile.size / 1024 / 1024).toFixed(1)} MB</p>}
            </div>
            {audioResult && (
              <div className={`mt-4 p-4 rounded-lg text-sm border ${audioResult.ok ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                <div className="flex items-center gap-2 mb-2">
                  {audioResult.ok ? <CheckCircle size={16} className="text-green-600" /> : <XCircle size={16} className="text-red-600" />}
                  <span className={audioResult.ok ? "text-green-700" : "text-red-700"}>{audioResult.msg}</span>
                </div>
                {audioResult.transcript && (
                  <div className="mt-2 p-3 bg-white rounded border border-gray-100 text-gray-700 max-h-48 overflow-y-auto whitespace-pre-wrap text-xs">
                    {audioResult.transcript}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
