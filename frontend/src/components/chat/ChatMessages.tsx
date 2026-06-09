"use client";
import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import MessageBubble from "./MessageBubble";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: { filename: string; similarity: number }[];
  agentType?: string;
  isThinking?: boolean;
}

interface ChatMessagesProps {
  messages: Message[];
  isStreaming: boolean;
  currentAgent?: string;
}

export default function ChatMessages({ messages, isStreaming, currentAgent }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isStreaming) {
      if (containerRef.current) {
        containerRef.current.scrollTop = containerRef.current.scrollHeight;
      }
    } else {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isStreaming]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center px-6"
        >
          <motion.div
            animate={{ y: [-4, 4, -4] }}
            transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
            className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center"
          >
            <svg className="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.625 9.75a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 01.778-.332 48.294 48.294 0 005.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
            </svg>
          </motion.div>
          <h3 className="text-lg font-semibold text-gray-700 mb-2">Start a Conversation</h3>
          <p className="text-sm text-gray-400 max-w-md">
            Ask questions about your uploaded documents. The AI will search your knowledge base and provide answers with source references.
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-3xl mx-auto">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => {
            const isLast = i === messages.length - 1;
            const isLastAssistant = isLast && msg.role === "assistant";
            const isStreamingLast = isLastAssistant && isStreaming;
            const isThinking = isLastAssistant && msg.content === "" && isStreaming;

            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: Math.min(i * 0.02, 0.3) }}
              >
                <MessageBubble
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                  isStreaming={isStreamingLast}
                  agentType={isLastAssistant ? (msg.agentType || currentAgent) : undefined}
                  isThinking={isThinking}
                />
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
