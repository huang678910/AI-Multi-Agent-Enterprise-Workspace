"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import {
  listMemories, createMemory, deleteMemory,
  recallMemories,
  listMemoryEvents, createMemoryEvent, deleteMemoryEvent,
} from "@/lib/api-client";
import type { MemoryResult, MemoryEventResult } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MemoryCard from "@/components/memories/MemoryCard";
import { Plus, Search, Trash2, History, Brain } from "lucide-react";
import WorkspaceSelector from "@/components/layout/WorkspaceSelector";

export default function MemoriesPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const [tab, setTab] = useState<"memories" | "events" | "recall">("memories");

  // Memories state
  const [memories, setMemories] = useState<MemoryResult[]>([]);
  const [typeFilter, setTypeFilter] = useState("");
  const [newMemory, setNewMemory] = useState({ title: "", content: "", memory_type: "long_term", importance: "5" });

  // Events state
  const [events, setEvents] = useState<MemoryEventResult[]>([]);

  // Recall state
  const [recallQuery, setRecallQuery] = useState("");
  const [recallResults, setRecallResults] = useState<MemoryResult[]>([]);
  const [recalling, setRecalling] = useState(false);

  useEffect(() => { if (!token) router.push("/login"); }, [token, router]);

  useEffect(() => { setMemories([]); setEvents([]); setRecallResults([]); }, [workspaceId]);

  const loadMemories = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await listMemories(workspaceId, typeFilter || undefined);
      setMemories(data);
    } catch {}
  }, [workspaceId, typeFilter]);

  const loadEvents = useCallback(async () => {
    if (!workspaceId) return;
    try { setEvents(await listMemoryEvents(workspaceId)); } catch {}
  }, [workspaceId]);

  useEffect(() => { loadMemories(); loadEvents(); }, [loadMemories, loadEvents]);

  const handleCreate = async () => {
    if (!workspaceId || !newMemory.title.trim() || !newMemory.content.trim()) return;
    await createMemory(workspaceId, {
      title: newMemory.title, content: newMemory.content,
      memory_type: newMemory.memory_type,
      importance: parseFloat(newMemory.importance) || 5,
    });
    setNewMemory({ title: "", content: "", memory_type: "long_term", importance: "5" });
    loadMemories();
  };

  const handleDelete = async (id: string) => {
    if (!workspaceId || !confirm("Delete this memory?")) return;
    await deleteMemory(workspaceId, id);
    loadMemories();
  };

  const handleRecall = async () => {
    if (!workspaceId || !recallQuery.trim()) return;
    setRecalling(true);
    try {
      setRecallResults(await recallMemories(workspaceId, recallQuery));
    } catch {}
    setRecalling(false);
  };

  if (!workspaceId) return <div className="p-8 text-gray-400">Select a workspace first.</div>;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <WorkspaceSelector />
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Enterprise Memory</h2>
          <p className="text-sm text-gray-500 mt-1">Long-term, episodic, and semantic memories. Memories are auto-extracted from conversations.</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {(["memories", "events", "recall"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? "bg-white text-gray-800 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}>
            {t === "memories" && <Brain size={14} />}
            {t === "events" && <History size={14} />}
            {t === "recall" && <Search size={14} />}
            {t === "memories" ? "Memories" : t === "events" ? "Event Timeline" : "Semantic Recall"}
          </button>
        ))}
      </div>

      {/* ─── Memories Tab ─────────────────────────────── */}
      {tab === "memories" && (
        <div className="space-y-4">
          {/* Create form */}
          <Card>
            <CardHeader><CardTitle className="text-base">Add Memory</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex gap-2">
                  <Input placeholder="Title" value={newMemory.title}
                    onChange={(e) => setNewMemory({ ...newMemory, title: e.target.value })} className="flex-1" />
                  <select value={newMemory.memory_type}
                    onChange={(e) => setNewMemory({ ...newMemory, memory_type: e.target.value })}
                    className="text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white w-36">
                    <option value="long_term">Long Term</option>
                    <option value="episodic">Episodic</option>
                    <option value="semantic">Semantic</option>
                  </select>
                  <Input placeholder="Importance (1-10)" type="number" value={newMemory.importance}
                    onChange={(e) => setNewMemory({ ...newMemory, importance: e.target.value })} className="w-36" />
                </div>
                <textarea
                  value={newMemory.content}
                  onChange={(e) => setNewMemory({ ...newMemory, content: e.target.value })}
                  placeholder="Memory content..."
                  rows={2}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <Button size="sm" onClick={handleCreate} disabled={!newMemory.title.trim()}>
                  <Plus size={14} className="mr-1" /> Save Memory
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Filter */}
          <div className="flex gap-2 items-center">
            <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); }}
              className="text-sm rounded-lg border border-gray-200 px-3 py-1.5 bg-white">
              <option value="">All Types</option>
              <option value="long_term">Long Term</option>
              <option value="episodic">Episodic</option>
              <option value="semantic">Semantic</option>
            </select>
            <span className="text-xs text-gray-400">{memories.length} memories</span>
          </div>

          {/* Memory grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {memories.map((m) => (
              <MemoryCard key={m.id} memory={m} onDelete={handleDelete} />
            ))}
            {memories.length === 0 && (
              <p className="text-sm text-gray-400 col-span-2 text-center py-8">
                No memories yet. They appear here when AI extracts them from conversations, or you can add one above.
              </p>
            )}
          </div>
        </div>
      )}

      {/* ─── Events Tab ───────────────────────────────── */}
      {tab === "events" && (
        <div className="space-y-3">
          {/* Quick add event */}
          <Card>
            <CardContent className="p-3">
              <div className="flex gap-2">
                <Input placeholder="Event title" className="flex-1" id="eventTitle" />
                <Input placeholder="Description (optional)" className="flex-1" id="eventDesc" />
                <select id="eventImpact" className="text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white w-28">
                  <option value="neutral">Neutral</option>
                  <option value="positive">Positive</option>
                  <option value="negative">Negative</option>
                </select>
                <Button size="sm" onClick={async () => {
                  const title = (document.getElementById('eventTitle') as HTMLInputElement)?.value;
                  const desc = (document.getElementById('eventDesc') as HTMLInputElement)?.value;
                  const impact = (document.getElementById('eventImpact') as HTMLSelectElement)?.value;
                  if (!workspaceId || !title?.trim()) return;
                  try {
                    await createMemoryEvent(workspaceId, { title, description: desc || undefined, impact, tags: [] });
                    (document.getElementById('eventTitle') as HTMLInputElement).value = '';
                    (document.getElementById('eventDesc') as HTMLInputElement).value = '';
                    loadEvents();
                  } catch (err) { console.error('Event create error:', err); }
                }}>
                  <Plus size={14} className="mr-1" /> Add Event
                </Button>
              </div>
            </CardContent>
          </Card>
          {/* Events list */}
          {events.map((e) => (
            <Card key={e.id} className="hover:shadow-sm transition-shadow group">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-medium text-gray-800">{e.title}</h3>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                        e.impact === "positive" ? "bg-green-50 text-green-600" :
                        e.impact === "negative" ? "bg-red-50 text-red-600" :
                        "bg-gray-50 text-gray-500"
                      }`}>{e.impact}</span>
                    </div>
                    {e.description && <p className="text-xs text-gray-500">{e.description}</p>}
                    <div className="flex gap-2 mt-2">
                      {e.event_date && <span className="text-[10px] text-gray-400">{e.event_date}</span>}
                      {e.tags?.map((t: string) => (
                        <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{t}</span>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={async () => {
                      if (!workspaceId || !confirm(`Delete event "${e.title}"? (Admin only)`)) return;
                      try { await deleteMemoryEvent(workspaceId, e.id); loadEvents(); }
                      catch (err: unknown) { alert(err instanceof Error ? err.message : "Delete failed — admin role required"); }
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 rounded transition-all flex-shrink-0"
                    title="Delete event (Admin only)">
                    <Trash2 size={14} className="text-red-400" />
                  </button>
                </div>
              </CardContent>
            </Card>
          ))}
          {events.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-8">No events recorded yet.</p>
          )}
        </div>
      )}

      {/* ─── Recall Tab ───────────────────────────────── */}
      {tab === "recall" && (
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Semantic Memory Search</CardTitle></CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input placeholder="Search memories... (e.g. 'what did we decide about pricing')"
                  value={recallQuery} onChange={(e) => setRecallQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleRecall()}
                  className="flex-1" />
                <Button onClick={handleRecall} disabled={recalling || !recallQuery.trim()}>
                  <Search size={14} className="mr-1" />
                  {recalling ? "Searching..." : "Recall"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {recallResults.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm text-gray-500">{recallResults.length} results</p>
              {recallResults.map((r) => (
                <Card key={r.id} className="hover:shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                        r.memory_type === "long_term" ? "bg-blue-50 text-blue-600" :
                        r.memory_type === "episodic" ? "bg-amber-50 text-amber-600" :
                        "bg-purple-50 text-purple-600"
                      }`}>{r.memory_type}</span>
                      <span className="text-[10px] text-gray-400">Score: {(r.similarity * 100).toFixed(0)}%</span>
                    </div>
                    <h3 className="text-sm font-medium">{r.title}</h3>
                    <p className="text-xs text-gray-500 mt-1">{r.content}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
