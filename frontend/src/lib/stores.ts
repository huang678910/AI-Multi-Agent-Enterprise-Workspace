"use client";
import { create } from "zustand";
import type { User } from "@/types";

// ---- Auth Store ----
interface AuthStore {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("token") : null,
  user: typeof window !== "undefined" ? (() => {
    const saved = localStorage.getItem("user");
    if (saved) {
      try {
        const u = JSON.parse(saved);
        if (u.id) return u;
      } catch { /* ignore corrupt data */ }
    }
    // Fallback: decode JWT sub as user ID
    const tok = localStorage.getItem("token");
    if (tok) {
      try {
        const payload = JSON.parse(atob(tok.split(".")[1]));
        return { id: payload.sub || "", email: "", username: "", is_active: true };
      } catch { /* ignore decode errors */ }
    }
    return null;
  })() : null,
  setAuth: (token, user) => {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("user");
    localStorage.removeItem("activeWorkspaceId");
    // 清空所有本地状态，防止下个用户看到上一用户数据
    useWorkspaceStore.setState({ activeWorkspaceId: null });
    useChatStore.setState({ messages: [], isStreaming: false, activeSessionId: null });
    set({ token: null, user: null });
  },
  isAuthenticated: () => !!get().token,
}));

// ---- Workspace Store ----
interface WorkspaceStore {
  activeWorkspaceId: string | null;
  setActiveWorkspace: (id: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  activeWorkspaceId: typeof window !== "undefined" ? localStorage.getItem("activeWorkspaceId") : null,
  setActiveWorkspace: (id) => {
    if (id) { localStorage.setItem("activeWorkspaceId", id); }
    else { localStorage.removeItem("activeWorkspaceId"); }
    set({ activeWorkspaceId: id });
  },
}));

// ---- Chat Store ----
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: { filename: string; chunk_id?: string; similarity: number }[];
}

interface ChatStore {
  messages: ChatMessage[];
  isStreaming: boolean;
  activeSessionId: string | null;
  addMessage: (msg: ChatMessage) => void;
  appendToLastAssistant: (token: string) => void;
  updateLastAssistantSources: (sources: { filename: string; chunk_id?: string; similarity: number }[]) => void;
  setStreaming: (v: boolean) => void;
  setActiveSession: (id: string | null) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isStreaming: false,
  activeSessionId: null,
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  appendToLastAssistant: (token) =>
    set((s) => {
      const msgs = [...s.messages];
      if (msgs.length > 0 && msgs[msgs.length - 1].role === "assistant") {
        msgs[msgs.length - 1] = {
          ...msgs[msgs.length - 1],
          content: msgs[msgs.length - 1].content + token,
        };
      } else {
        msgs.push({ role: "assistant", content: token });
      }
      return { messages: msgs };
    }),
  updateLastAssistantSources: (sources) =>
    set((s) => {
      const msgs = [...s.messages];
      if (msgs.length > 0 && msgs[msgs.length - 1].role === "assistant") {
        msgs[msgs.length - 1] = {
          ...msgs[msgs.length - 1],
          sources,
        };
      }
      return { messages: msgs };
    }),
  setStreaming: (v) => set({ isStreaming: v }),
  setActiveSession: (id) => set({ activeSessionId: id }),
  clearMessages: () => set({ messages: [] }),
}));
