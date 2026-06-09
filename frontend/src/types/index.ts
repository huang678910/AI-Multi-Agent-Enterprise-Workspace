// ---- Auth ----
export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

// ---- Workspace ----
export interface Workspace {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

// ---- Document ----
export type DocumentStatus = "pending" | "processing" | "ready" | "error";

export interface Document {
  id: string;
  workspace_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
}

// ---- Chat ----
export interface ChatSession {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources: Source[] | null;
  created_at: string;
}

export interface Source {
  filename: string;
  chunk_id?: string;
  similarity: number;
}

// ---- Search ----
export interface SearchResult {
  chunk_id: string;
  document_id: string;
  filename: string;
  content: string;
  metadata: Record<string, unknown> | null;
  similarity: number;
}

// ---- SSE Events ----
export type SSEEventType = "token" | "done" | "error" | "status";

export interface SSEEvent {
  type: SSEEventType;
  content: string;
  sources?: Source[];
}

// ---- WebSocket Events ----
export interface WSConnectedEvent {
  type: "connected";
  data: {
    session_id: string;
    workspace_id: string;
  };
}

export interface WSTokenEvent {
  type: "token";
  content: string;
}

export interface WSStatusEvent {
  type: "status";
  content: string;
  agent?: string;
}

export interface WSDoneEvent {
  type: "done";
  content: string;
  sources?: Source[];
}

export interface WSErrorEvent {
  type: "error";
  content: string;
  code?: string;
}

export type WSServerEvent = WSConnectedEvent | WSTokenEvent | WSStatusEvent | WSDoneEvent | WSErrorEvent;

export interface WSClientMessage {
  type: "message" | "cancel" | "ping";
  data?: {
    content: string;
  };
}
