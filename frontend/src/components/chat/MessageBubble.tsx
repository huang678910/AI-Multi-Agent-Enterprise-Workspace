"use client";
import ReactMarkdown from "react-markdown";
import { motion } from "framer-motion";
import { Bot, Search, MessageCircle } from "lucide-react";
import type { Source } from "@/types";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isStreaming?: boolean;
  agentType?: string;  // "search" | "chat" | "supervisor"
  isThinking?: boolean;
}

const AGENT_LABELS: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  search: { icon: <Search size={12} />, label: "Search Agent", color: "text-purple-500 bg-purple-50" },
  chat: { icon: <MessageCircle size={12} />, label: "Chat Agent", color: "text-blue-500 bg-blue-50" },
  supervisor: { icon: <Bot size={12} />, label: "Supervisor", color: "text-amber-500 bg-amber-50" },
};

export default function MessageBubble({ role, content, sources, isStreaming, agentType, isThinking }: MessageBubbleProps) {
  const isUser = role === "user";
  const agent = agentType ? AGENT_LABELS[agentType] : null;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-5 py-3 ${
          isUser
            ? "bg-blue-500 text-white rounded-br-md"
            : "bg-white border border-gray-100 shadow-sm rounded-bl-md"
        }`}
      >
        {/* Agent Badge with spring animation */}
        {agent && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 400, damping: 20 }}
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-medium mb-2 ${agent.color}`}
          >
            {agent.icon}
            {agent.label}
          </motion.div>
        )}

        {/* Thinking indicator */}
        {isThinking && content === "" && (
          <div className="flex items-center gap-2 text-sm text-gray-400 py-1">
            <Bot size={14} className="animate-pulse" />
            <span className="animate-pulse">Thinking...</span>
          </div>
        )}

        {/* Content */}
        <div className={`text-sm leading-relaxed ${isUser ? "" : "markdown-body"}`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : content ? (
            // Defer markdown parsing during streaming to prevent per-token DOM rebuilds
            isStreaming ? (
              <p className="whitespace-pre-wrap">{content}</p>
            ) : (
              <ReactMarkdown>{content}</ReactMarkdown>
            )
          ) : null}
          {isStreaming && (
            <span className="inline-block w-1.5 h-4 bg-blue-500 animate-pulse ml-0.5 align-middle rounded-sm" style={{ willChange: "transform" }} />
          )}
        </div>

        {/* Sources — shown after completion */}
        {sources && sources.length > 0 && !isStreaming && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-xs text-gray-400 mb-1.5 font-medium">Sources:</p>
            <div className="flex flex-wrap gap-1.5">
              {sources.map((s, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-medium"
                >
                  {s.filename} ({(s.similarity * 100).toFixed(0)}%)
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
