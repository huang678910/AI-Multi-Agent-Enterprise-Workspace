"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { useAuthStore, useChatStore, useWorkspaceStore } from "@/lib/stores";
import {
  listWorkspaces,
  createWorkspace,
  deleteWorkspace,
  listChatSessions,
  createChatSession,
  deleteChatSession,
  listMessages,
  sendChatMessage,
} from "@/lib/api-client";
import { WebSocketClient } from "@/lib/websocket-client";
import type { Workspace, ChatSession, Source } from "@/types";
import ChatMessages from "@/components/chat/ChatMessages";
import ChatInput from "@/components/chat/ChatInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ChatPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);

  const {
    messages, isStreaming, addMessage, appendToLastAssistant,
    updateLastAssistantSources, setStreaming, activeSessionId,
    setActiveSession, clearMessages,
  } = useChatStore();

  const { activeWorkspaceId, setActiveWorkspace } = useWorkspaceStore();

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [newWsName, setNewWsName] = useState("");
  const [showNewWs, setShowNewWs] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<string>("");

  // 持久化 WS 客户端引用（不随渲染重建）
  const wsRef = useRef<WebSocketClient | null>(null);
  const currentSessionRef = useRef<string | null>(null);
  const currentWorkspaceRef = useRef<string | null>(null);

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

  // Load sessions when workspace changes — auto-create if none
  useEffect(() => {
    if (!activeWorkspaceId || !token) return;
    listChatSessions(activeWorkspaceId)
      .then(async (d) => {
        setSessions(d.sessions);
        if (d.sessions.length > 0) {
          setActiveSession(d.sessions[0].id);
        } else {
          try {
            const s = await createChatSession(activeWorkspaceId);
            setSessions([s]);
            setActiveSession(s.id);
          } catch (err) {
            console.error("Failed to auto-create session:", err);
          }
        }
      })
      .catch(() => {});
  }, [activeWorkspaceId, token]);


  // Load messages when session changes
  useEffect(() => {
    if (!activeWorkspaceId || !activeSessionId || !token) return;
    let cancelled = false;

    listMessages(activeWorkspaceId, activeSessionId)
      .then((msgs) => {
        if (cancelled) return;
        // 原子替换整个消息列表，避免 clearMessages + addMessage 的竞态条件
        useChatStore.setState({
          messages: msgs.map((m: { role: string; content: string; sources?: unknown[] }) => ({
            role: m.role as "user" | "assistant",
            content: m.content,
            sources: m.sources as Source[] | undefined,
          })),
        });
      })
      .catch(() => {});

    return () => { cancelled = true; };
  }, [activeSessionId, activeWorkspaceId, token]);

  // ---- WebSocket 连接管理 ----
  useEffect(() => {
    if (!token || !activeSessionId || !activeWorkspaceId) return;

    // 如果会话和工作区没变，不重连
    if (
      currentSessionRef.current === activeSessionId &&
      currentWorkspaceRef.current === activeWorkspaceId &&
      wsRef.current?.isConnected
    ) {
      return;
    }

    // 断开旧连接
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }

    currentSessionRef.current = activeSessionId;
    currentWorkspaceRef.current = activeWorkspaceId;

    // 创建新的 WS 客户端
    const ws = new WebSocketClient(token);
    wsRef.current = ws;

    // 绑定事件处理器
    const unsubs: (() => void)[] = [];

    unsubs.push(ws.on("connected", () => {
      console.log("[Chat] WebSocket connected");
      setWsConnected(true);
    }));

    unsubs.push(ws.on("token", (msg) => {
      const content = msg.data?.content || msg.content || "";
      if (content) {
        appendToLastAssistant(content);
      }
    }));

    unsubs.push(ws.on("status", (msg) => {
      const content = msg.data?.content || msg.content || "";
      const agent = msg.data?.agent || msg.agent || "";
      console.log("[Chat] Agent status:", content, agent);
      if (agent) setCurrentAgent(agent);
    }));

    unsubs.push(ws.on("done", (msg) => {
      const sources = msg.data?.sources || msg.sources;
      if (sources && sources.length > 0) {
        updateLastAssistantSources(sources as Source[]);
      }
      setStreaming(false);

      // 刷新会话列表（标题可能已更新）
      if (activeWorkspaceId) {
        listChatSessions(activeWorkspaceId).then((d) => setSessions(d.sessions)).catch(() => {});
      }
    }));

    unsubs.push(ws.on("error", (msg) => {
      const content = msg.data?.content || msg.content || "Unknown error";
      appendToLastAssistant(`\n\n❌ Error: ${content}`);
      setStreaming(false);
    }));

    unsubs.push(ws.on("pong", () => {
      // 心跳响应，无需处理
    }));

    // 开始连接
    ws.connect(activeSessionId, activeWorkspaceId);

    return () => {
      // 清理
      unsubs.forEach((f) => f());
      ws.disconnect();
      wsRef.current = null;
      setWsConnected(false);
      setStreaming(false);
      setCurrentAgent("");
      currentSessionRef.current = null;
      currentWorkspaceRef.current = null;
    };
  }, [activeSessionId, activeWorkspaceId, token]);

  async function handleDeleteWorkspace(wsId: string, wsName: string) {
    if (!confirm(`Delete workspace "${wsName}" and all its data? This cannot be undone.`)) return;
    try {
      await deleteWorkspace(wsId);
      setWorkspaces((prev) => prev.filter((w) => w.id !== wsId));
      if (activeWorkspaceId === wsId) {
        setActiveWorkspace(null);
        setActiveSession(null);
        clearMessages();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      alert("Failed to delete workspace: " + msg);
    }
  }

  async function handleCreateWorkspace() {
    if (!newWsName.trim()) return;
    try {
      const ws = await createWorkspace(newWsName);
      setWorkspaces((prev) => [ws, ...prev]);
      setActiveWorkspace(ws.id);
      setNewWsName("");
      setShowNewWs(false);
    } catch (err) {
      console.error("Failed to create workspace:", err);
    }
  }

  async function handleNewSession() {
    if (!activeWorkspaceId) return;
    try {
      const s = await createChatSession(activeWorkspaceId);
      setSessions((prev) => [s, ...prev]);
      setActiveSession(s.id);
      clearMessages();
      setStreaming(false);
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  }

  async function handleDeleteSession(sid: string) {
    if (!activeWorkspaceId) return;
    await deleteChatSession(activeWorkspaceId, sid);
    setSessions((prev) => prev.filter((s) => s.id !== sid));
    if (activeSessionId === sid) {
      setActiveSession(null);
    }
  }

  const handleSend = useCallback((message: string) => {
    if (!activeWorkspaceId || !activeSessionId || isStreaming) return;

    const ws = wsRef.current;
    if (!ws?.isConnected) {
      console.warn("[Chat] WebSocket not connected — cannot send");
      // 降级：用 HTTP 发送（如果 WS 不可用）
      addMessage({ role: "user", content: message });
      addMessage({ role: "assistant", content: "" });
      setStreaming(true);
      sendChatMessage(activeWorkspaceId!, activeSessionId!, message)
        .then((result) => {
          const msgs = useChatStore.getState().messages;
          const lastIdx = msgs.length - 1;
          if (lastIdx >= 0 && msgs[lastIdx].role === "assistant") {
            msgs[lastIdx] = {
              role: "assistant",
              content: result.reply,
              sources: result.sources as Source[] | undefined,
            };
            useChatStore.setState({ messages: [...msgs] });
          }
        })
        .catch((err: Error) => {
          appendToLastAssistant(`\n\n❌ Error: ${err.message}`);
        })
        .finally(() => {
          setStreaming(false);
          listChatSessions(activeWorkspaceId!).then((d) => setSessions(d.sessions)).catch(() => {});
        });
      return;
    }

    // WebSocket 发送
    addMessage({ role: "user", content: message });
    addMessage({ role: "assistant", content: "" });
    setStreaming(true);
    setCurrentAgent("");

    ws.send({ type: "message", data: { content: message } });
  }, [activeWorkspaceId, activeSessionId, isStreaming, addMessage, appendToLastAssistant, setStreaming]);

  const currentWs = workspaces.find((w) => w.id === activeWorkspaceId);

  // Agent status label
  const agentLabel = currentAgent
    ? currentAgent.charAt(0).toUpperCase() + currentAgent.slice(1)
    : "";

  return (
    <div className="flex h-full">
      {/* Sessions Sidebar */}
      <div className="w-64 border-r border-gray-200 bg-white flex flex-col">
        {/* Workspace Selector */}
        <div className="p-4 border-b border-gray-100">
          <label className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Workspace</label>
          <select
            value={activeWorkspaceId || ""}
            onChange={(e) => {
              setActiveWorkspace(e.target.value);
              setActiveSession(null);
              clearMessages();
              setStreaming(false);
              setCurrentAgent("");
            }}
            className="mt-1 w-full text-sm rounded-lg border border-gray-200 px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
          {activeWorkspaceId && (
            <button
              onClick={() => handleDeleteWorkspace(activeWorkspaceId, currentWs?.name || "")}
              className="ml-2 p-1.5 hover:bg-red-50 rounded transition-colors text-gray-400 hover:text-red-500"
              title="Delete workspace"
            >
              <Trash2 size={14} />
            </button>
          )}
          {showNewWs ? (
            <div className="flex gap-1 mt-2">
              <Input
                value={newWsName}
                onChange={(e) => setNewWsName(e.target.value)}
                placeholder="Workspace name"
                className="h-8 text-xs"
                onKeyDown={(e) => e.key === "Enter" && handleCreateWorkspace()}
              />
              <Button size="sm" onClick={handleCreateWorkspace} className="h-8 text-xs">Add</Button>
            </div>
          ) : (
            <button
              onClick={() => setShowNewWs(true)}
              className="text-xs text-blue-500 hover:text-blue-700 mt-2"
            >
              + New Workspace
            </button>
          )}
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-xs text-gray-400 font-medium">Chats</span>
            <button onClick={handleNewSession} className="p-1 hover:bg-gray-100 rounded" title="New Chat">
              <Plus size={16} className="text-gray-400" />
            </button>
          </div>
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => { setActiveSession(s.id); clearMessages(); setStreaming(false); }}
              className={`flex items-center justify-between px-4 py-2.5 mx-2 rounded-lg cursor-pointer text-sm group transition-colors ${
                activeSessionId === s.id
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center gap-2 truncate">
                <MessageSquare size={14} className="flex-shrink-0" />
                <span className="truncate">{s.title}</span>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }}
                className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-50 rounded transition-all"
              >
                <Trash2 size={12} className="text-red-400" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-white flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
              {currentWs?.name || "Chat"}
              {/* WebSocket 连接指示器 */}
              <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-normal ${
                wsConnected ? "bg-green-50 text-green-600" : "bg-red-50 text-red-400"
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? "bg-green-500 animate-pulse" : "bg-red-400"}`} />
                {wsConnected ? "WS Live" : "WS Offline"}
              </span>
              {/* Agent indicator */}
              {isStreaming && agentLabel && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 font-normal animate-pulse">
                  {agentLabel}
                </span>
              )}
            </h2>
            <p className="text-xs text-gray-400">
              {currentWs ? `${currentWs.description || "No description"}` : "Select a workspace"}
            </p>
          </div>
        </div>

        {/* Messages */}
        <ChatMessages messages={messages} isStreaming={isStreaming} currentAgent={currentAgent} />

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={isStreaming || !activeSessionId} />
      </div>
    </div>
  );
}
