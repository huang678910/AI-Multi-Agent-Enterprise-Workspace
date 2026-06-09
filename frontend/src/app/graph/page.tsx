"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import { searchGraph, getGraphStats, syncGraph } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import WorkspaceSelector from "@/components/layout/WorkspaceSelector";
import { Search, RefreshCw, Network, Users, Package, Target } from "lucide-react";

interface GraphNode {
  entity: string;
  type: string[];
  related: { relationship: string; entity: string }[];
}

export default function GraphPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const workspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  const [results, setResults] = useState<GraphNode[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [stats, setStats] = useState<{ nodes: number; relationships: number; labels: { label: string; count: number }[]; connected: boolean } | null>(null);

  useEffect(() => { if (!token) router.push("/login"); }, [token, router]);

  useEffect(() => { setResults([]); setError(""); }, [workspaceId]);

  const loadStats = useCallback(async () => {
    if (!workspaceId) return;
    try { setStats(await getGraphStats(workspaceId)); } catch {}
  }, [workspaceId]);

  useEffect(() => { loadStats(); }, [loadStats]);

  const handleSearch = async () => {
    if (!workspaceId) return;
    if (!searchQuery.trim()) { setError("Please enter a search query"); return; }
    setSearching(true);
    setError("");
    setResults([]);
    try {
      console.log("[Graph] Searching:", searchQuery);
      const data = await searchGraph(workspaceId, searchQuery);
      setResults(data.results || []);
      if (!data.results || data.results.length === 0) {
        const nodeCount = stats?.nodes || 0;
        if (nodeCount === 0) {
          setError("Graph is empty. First create company data in Settings (Departments, Products, etc.), then click 'Sync from DB'.");
        } else {
          setError(`No entities match "${searchQuery}". Graph has ${nodeCount} nodes. Try: ${stats?.labels?.map(l => l.label).join(', ') || 'syncing first'}.`);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Search failed";
      setError(msg);
      console.error("[Graph] Search error:", err);
    } finally {
      setSearching(false);
    }
  };

  const handleSync = async () => {
    if (!workspaceId) return;
    setSyncing(true);
    setError("");
    try {
      console.log("[Graph] Syncing...");
      await syncGraph(workspaceId);
      loadStats();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Sync failed";
      setError(msg);
      console.error("[Graph] Sync error:", err);
    } finally {
      setSyncing(false);
    }
  };

  const labelIcons: Record<string, React.ReactNode> = {
    Employee: <Users size={14} />,
    Department: <Network size={14} />,
    Product: <Package size={14} />,
    Goal: <Target size={14} />,
  };

  if (!workspaceId) return <div className="p-8 text-gray-400 text-center">Select a workspace first.</div>;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <WorkspaceSelector />
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Knowledge Graph</h2>
          <p className="text-sm text-gray-500 mt-1">Explore entity relationships in your enterprise.</p>
        </div>
        <Button onClick={handleSync} disabled={syncing} variant="outline" size="sm">
          <RefreshCw size={14} className={`mr-1 ${syncing ? "animate-spin" : ""}`} />
          {syncing ? "Syncing..." : "Sync from DB"}
        </Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          <Card><CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{stats.nodes}</p><p className="text-xs text-gray-400">Nodes</p>
          </CardContent></Card>
          <Card><CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{stats.relationships}</p><p className="text-xs text-gray-400">Relationships</p>
          </CardContent></Card>
          <Card><CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{stats.labels.length}</p><p className="text-xs text-gray-400">Entity Types</p>
          </CardContent></Card>
          <Card><CardContent className="p-4 text-center">
            <div className={`w-3 h-3 rounded-full mx-auto mb-1 ${stats.connected ? "bg-green-500" : "bg-red-400"}`} />
            <p className="text-xs text-gray-400">{stats.connected ? "Neo4j Online" : "Offline"}</p>
          </CardContent></Card>
        </div>
      )}

      {stats?.labels && stats.labels.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {stats.labels.map((l) => (
            <span key={l.label} className="inline-flex items-center gap-1 text-xs px-3 py-1 rounded-full bg-gray-100 text-gray-600">
              {labelIcons[l.label] || null} {l.label}: {l.count}
            </span>
          ))}
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Search */}
      <Card>
        <CardHeader><CardTitle className="text-base">Explore Graph</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder='Search entities... (e.g. "who works in sales", "toys")'
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setError(""); }}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1"
            />
            <Button onClick={handleSearch} disabled={searching}>
              <Search size={14} className="mr-1" />
              {searching ? "Searching..." : "Search"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">{results.length} entities found</p>
          {results.map((node, i) => (
            <Card key={i} className="hover:shadow-sm">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                    <span className="text-blue-600 font-bold text-sm">{node.entity.charAt(0).toUpperCase()}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-sm font-semibold text-gray-800">{node.entity}</h3>
                      {node.type.map((t) => (
                        <span key={t} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600">{t}</span>
                      ))}
                    </div>
                    {node.related.length > 0 && (
                      <div className="space-y-1">
                        {node.related.map((r, j) => (
                          <div key={j} className="flex items-center gap-2 text-xs">
                            <span className="text-gray-400">└</span>
                            <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 font-mono text-[10px]">{r.relationship}</span>
                            <span className="text-gray-600">→</span>
                            <span className="text-gray-700 font-medium">{r.entity}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!stats?.connected && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="p-4 text-center">
            <p className="text-sm text-amber-700">
              Neo4j is not connected. Run <code className="bg-amber-100 px-1 rounded">docker-compose up -d neo4j</code> to start the graph database,
              then click "Sync from DB" to populate the knowledge graph.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
