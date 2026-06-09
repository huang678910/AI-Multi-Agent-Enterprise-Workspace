"use client";

// ---- WebSocket 消息类型 ----

export interface WSClientMessage {
  type: "message" | "cancel" | "ping";
  data?: {
    content: string;
  };
}

export interface WSServerMessage {
  type: "connected" | "status" | "token" | "done" | "error" | "pong";
  data?: {
    content?: string;
    session_id?: string;
    workspace_id?: string;
    sources?: { filename: string; chunk_id?: string; similarity: number }[];
    code?: string;
    agent?: string;
  };
  // Legacy: top-level fields for backward compat
  content?: string;
  sources?: { filename: string; chunk_id?: string; similarity: number }[];
  agent?: string;
}

export type WSEventHandler = (msg: WSServerMessage) => void;

// ---- WebSocket 客户端 ----

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, WSEventHandler[]> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private token: string;
  private _isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 10;

  constructor(token: string) {
    this.token = token;
    const base =
      process.env.NEXT_PUBLIC_WS_URL ||
      process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, "ws") ||
      "ws://localhost:8000";
    this.url = base;
  }

  get isConnected(): boolean {
    return this._isConnected;
  }

  connect(sessionId: string, workspaceId: string) {
    // 关闭旧 WebSocket 连接（保留事件处理器！）
    this._closeSocket();

    const wsUrl = `${this.url}/api/v1/ws/chat?token=${encodeURIComponent(this.token)}&session_id=${encodeURIComponent(sessionId)}&workspace_id=${encodeURIComponent(workspaceId)}`;
    console.log("[WS] Connecting:", wsUrl.replace(this.token, "***"));

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("[WS] Connected");
        this._isConnected = true;
        this.reconnectAttempts = 0;
        this.startPing();
        this._emit({ type: "connected" });
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const msg: WSServerMessage = JSON.parse(event.data as string);
          // 规范化消息（兼容新旧格式）
          if (!msg.data && (msg.content || msg.sources)) {
            msg.data = {
              content: msg.content,
              sources: msg.sources,
              agent: msg.agent,
            };
          }
          this._emit(msg);
        } catch {
          console.warn("[WS] Failed to parse message:", event.data);
        }
      };

      this.ws.onclose = (event: CloseEvent) => {
        console.log(`[WS] Closed: code=${event.code} reason=${event.reason}`);
        this._isConnected = false;
        this.stopPing();

        // 非正常关闭则自动重连（不清除处理器！）
        if (event.code !== 1000 && event.code !== 4001) {
          this.scheduleReconnect(sessionId, workspaceId);
        }
      };

      this.ws.onerror = () => {
        console.error("[WS] Error — connection will close");
        this._isConnected = false;
      };
    } catch (err) {
      console.error("[WS] Failed to create WebSocket:", err);
      this.scheduleReconnect(sessionId, workspaceId);
    }
  }

  send(msg: WSClientMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    } else {
      console.warn("[WS] Cannot send — not connected");
    }
  }

  on(eventType: string, handler: WSEventHandler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType)!.push(handler);
    return () => this.off(eventType, handler);
  }

  off(eventType: string, handler: WSEventHandler) {
    const handlers = this.handlers.get(eventType);
    if (handlers) {
      const idx = handlers.indexOf(handler);
      if (idx >= 0) handlers.splice(idx, 1);
    }
  }

  /** 关闭 WebSocket 连接并清理所有处理器（组件卸载时调用） */
  disconnect() {
    this._isConnected = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.stopPing();
    this._closeSocket();
    // 仅在组件完全卸载时清除处理器
    this.handlers.clear();
  }

  /** 仅关闭 WebSocket socket，保留事件处理器（用于重连时内部使用） */
  private _closeSocket() {
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
  }

  private _emit(msg: WSServerMessage) {
    const type = msg.type;
    const handlers = this.handlers.get(type) || [];
    handlers.forEach((h) => {
      try {
        h(msg);
      } catch (err) {
        console.error(`[WS] Handler error for ${type}:`, err);
      }
    });
  }

  private startPing() {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      this.send({ type: "ping" });
    }, 30000);
  }

  private stopPing() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect(sessionId: string, workspaceId: string) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log("[WS] Max reconnect attempts reached");
      return;
    }
    // 指数退避：3s, 6s, 12s, ... 最大 30s
    const delay = Math.min(3000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    this.reconnectTimer = setTimeout(() => {
      this.connect(sessionId, workspaceId);
    }, delay);
  }
}
