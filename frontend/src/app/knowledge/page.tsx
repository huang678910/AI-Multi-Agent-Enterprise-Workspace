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
import { Search, FileText, GitFork, Mic, Upload, CheckCircle, XCircle, Loader2 } from "lucide-react";
import api from "@/lib/api";

export default function KnowledgePage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const { activeWorkspaceId, setActiveWorkspace } = useWorkspaceStore();

  const [tab, setTab] = useState<"search" | "github" | "audio">("search");
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  // GitHub state
  const [ghForm, setGhForm] = useState({ token: "", owner: "", repo: "" });
  const [ghSyncing, setGhSyncing] = useState(false);
  const [ghResult, setGhResult] = useState<{ ok: boolean; msg: string } | null>(null);
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
    } catch (err) {
      console.error("Search failed:", err);
    } finally { setSearching(false); }
  }

  async function handleGitHubConnect() {
    if (!activeWorkspaceId) return;
    if (!ghForm.token.trim() || !ghForm.owner.trim() || !ghForm.repo.trim()) {
      setGhResult({ ok: false, msg: "Token, owner, and repo are all required" });
      return;
    }
    setGhSyncing(true);
    setGhResult(null);
    try {
      const res = await api.post(`/api/v1/workspaces/${activeWorkspaceId}/knowledge/connect/github`, ghForm);
      const data = res.data;
      if (data.error) {
        setGhResult({ ok: false, msg: data.error });
      } else {
        setGhResult({ ok: true, msg: data.message || `Synced ${data.synced} items` });
        setGhForm({ token: "", owner: "", repo: "" });
        loadConnections();
        // Refresh documents
        listDocuments(activeWorkspaceId).then((d) => setDocuments(d.documents)).catch(() => {});
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setGhResult({ ok: false, msg: detail || "Connection failed" });
    } finally { setGhSyncing(false); }
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
        setAudioResult({
          ok: true,
          msg: `Transcribed ${data.full_length} characters`,
          transcript: data.transcript,
          docId: data.document_id,
        });
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

      {/* Workspace selector */}
      <div className="mb-6">
        <select value={activeWorkspaceId || ""}
          onChange={(e) => setActiveWorkspace(e.target.value)}
          className="text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
          {workspaces.map((w) => (<option key={w.id} value={w.id}>{w.name}</option>))}
        </select>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit mb-6">
        {(["search", "github", "audio"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? "bg-white text-gray-800 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}>
            {t === "search" && <Search size={14} />}
            {t === "github" && <GitFork size={14} />}
            {t === "audio" && <Mic size={14} />}
            {t === "search" ? "Search" : t === "github" ? "GitHub Sync" : "Audio Transcription"}
          </button>
        ))}
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

      {/* ─── GitHub Tab ────────────────────────────────── */}
      {tab === "github" && (
        <div className="space-y-6">
          <Card>
            <CardContent className="p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                <GitFork size={16} /> Connect GitHub Repository
              </h3>
              <p className="text-xs text-gray-500 mb-4">
                Enter a GitHub repo to sync its README and recent Issues into your knowledge base.{" "}
                <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer"
                  className="text-blue-500 hover:underline">Get a token →</a>{" "}
                (needs <code className="bg-gray-100 px-1 rounded">repo</code> scope)
              </p>
              <div className="space-y-3">
                <div className="flex gap-2">
                  <Input placeholder="GitHub Token (ghp_...)" value={ghForm.token}
                    onChange={(e) => { setGhForm({ ...ghForm, token: e.target.value }); setGhResult(null); }}
                    type="password" className="flex-1" />
                </div>
                <div className="flex gap-2">
                  <Input placeholder="Owner (e.g. facebook)" value={ghForm.owner}
                    onChange={(e) => { setGhForm({ ...ghForm, owner: e.target.value }); setGhResult(null); }}
                    className="flex-1" />
                  <Input placeholder="Repo (e.g. react)" value={ghForm.repo}
                    onChange={(e) => { setGhForm({ ...ghForm, repo: e.target.value }); setGhResult(null); }}
                    className="flex-1" />
                </div>
                <Button onClick={handleGitHubConnect} disabled={ghSyncing} className="w-full sm:w-auto">
                  {ghSyncing ? <><Loader2 size={14} className="mr-1 animate-spin" /> Syncing...</> : <><Upload size={14} className="mr-1" /> Sync Repository</>}
                </Button>
              </div>
              {ghResult && (
                <div className={`mt-4 p-3 rounded-lg text-sm flex items-center gap-2 ${
                  ghResult.ok ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"
                }`}>
                  {ghResult.ok ? <CheckCircle size={16} /> : <XCircle size={16} />}
                  {ghResult.msg}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Connections List */}
          <Card>
            <CardContent className="p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Active Connections</h3>
              {connections.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">No external connections yet. Connect a GitHub repo above.</p>
              ) : (
                <div className="space-y-2">
                  {connections.map((c, i) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-gray-100 bg-gray-50">
                      <div className="flex items-center gap-2">
                        <GitFork size={14} className="text-gray-500" />
                        <span className="text-sm font-medium text-gray-700">{c.source_type}</span>
                        <span className="text-xs text-gray-400">{c.doc_count} document{c.doc_count !== 1 ? "s" : ""}</span>
                      </div>
                      <span className="text-xs text-gray-400">
                        Last synced: {c.last_synced ? new Date(c.last_synced).toLocaleString() : "N/A"}
                      </span>
                    </div>
                  ))}
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
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) { setAudioFile(f); setAudioResult(null); }
                    }} />
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
              {audioFile && (
                <p className="text-xs text-gray-400">
                  {(audioFile.size / 1024 / 1024).toFixed(1)} MB
                </p>
              )}
            </div>
            {audioResult && (
              <div className={`mt-4 p-4 rounded-lg text-sm border ${
                audioResult.ok ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
              }`}>
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
