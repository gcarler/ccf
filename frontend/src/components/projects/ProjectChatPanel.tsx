"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { useWorkspaceSocket } from "@/hooks/useWorkspaceSocket";
import { Send, Trash2, MessageSquare } from "lucide-react";

interface ChatMessage {
  id: number;
  sender_id: number;
  sender_name: string;
  content: string;
  created_at: string;
  is_read: boolean;
}

interface ProjectChatPanelProps {
  projectId: string;
}

export default function ProjectChatPanel({ projectId }: ProjectChatPanelProps) {
  const { token, user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userId = user?.id;

  useEffect(() => {
    if (!token || !projectId) return;
    setLoading(true);
    apiFetch<ChatMessage[]>(`/projects/${projectId}/messages`, {
      token,
      query: { limit: "100" },
    })
      .then((data) => {
        if (Array.isArray(data)) {
          setMessages(data.reverse());
        } else {
          setMessages([]);
        }
      })
      .catch(() => setMessages([]))
      .finally(() => setLoading(false));
  }, [projectId, token]);

  const handleSocketEvent = useCallback(
    (payload: any) => {
      if (payload?.event === "project_message" && payload?.project_id === projectId) {
        setMessages((prev) => [...prev, payload.message]);
      }
    },
    [projectId]
  );

  useWorkspaceSocket({
    rooms: [`project_${projectId}`],
    enabled: !!token,
    onEvent: handleSocketEvent,
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !token) return;
    try {
      const msg = await apiFetch<ChatMessage>(`/projects/${projectId}/messages`, {
        method: "POST",
        token,
        body: { content: input.trim() },
      });
      setMessages((prev) => [...prev, msg]);
      setInput("");
    } catch (err) {
      console.error("Failed to send message", err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleDelete = async (msgId: number, senderId: number) => {
    if (!token || senderId !== userId) return;
    try {
      await apiFetch(`/projects/${projectId}/messages/${msgId}`, {
        method: "DELETE",
        token,
      });
      setMessages((prev) => prev.filter((m) => m.id !== msgId));
    } catch (err) {
      console.error("Failed to delete message", err);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-[hsl(var(--text-secondary))] text-sm">
        Cargando mensajes...
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21]">
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-[hsl(var(--text-secondary))] gap-2">
          <MessageSquare className="w-10 h-10 opacity-40" />
          <p className="text-sm">No hay mensajes aún. ¡Sé el primero en escribir!</p>
        </div>
      ) : (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 space-y-3"
        >
          {messages.map((msg) => {
            const isOwn = msg.sender_id === userId;
            return (
              <div
                key={msg.id}
                className={`flex ${isOwn ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`relative group max-w-[75%] rounded-2xl px-4 py-2 ${
                    isOwn
                      ? "bg-[hsl(var(--primary))] text-white rounded-br-md"
                      : "bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] rounded-bl-md"
                  }`}
                >
                  {!isOwn && (
                    <p className="text-xs font-semibold mb-1 opacity-70">
                      {msg.sender_name}
                    </p>
                  )}
                  <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                  <div className="flex items-center justify-end gap-1 mt-1">
                    <span
                      className={`text-[10px] ${
                        isOwn ? "text-blue-200" : "text-[hsl(var(--text-secondary))]"
                      }`}
                    >
                      {new Date(msg.created_at).toLocaleTimeString("es-CO", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    {isOwn && (
                      <button
                        onClick={() => handleDelete(msg.id, msg.sender_id)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] hover:text-red-300"
                        title="Eliminar"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <div className="border-t border-[hsl(var(--border-primary))] dark:border-gray-700 p-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe un mensaje..."
            className="flex-1 px-4 py-2 rounded-full border border-[hsl(var(--border-primary))] dark:border-gray-600 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 dark:text-white"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="p-2 rounded-full bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary))] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
