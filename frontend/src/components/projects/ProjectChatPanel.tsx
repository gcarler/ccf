"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { useWorkspaceSocket } from "@/hooks/useWorkspaceSocket";
import { Send, Trash2, MessageSquare } from "lucide-react";
import { toast } from "sonner";

interface ChatMessage {
  id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  created_at: string;
  is_read: boolean;
}

interface ProjectChatPanelProps {
  projectId: string;
}

function formatMessageTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / 86400000);
  
  if (days === 0) {
    return date.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
  }
  if (days === 1) return "Ayer";
  if (days < 7) return `Hace ${days}d`;
  return date.toLocaleDateString("es-CO", { day: "2-digit", month: "short" });
}

export default function ProjectChatPanel({ projectId }: ProjectChatPanelProps) {
  const { token, user, loading: authLoading } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userId = user?.id;
  const shouldAutoScroll = useRef(true);

  // Track if user is near bottom to auto-scroll on new messages
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const threshold = 100;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    setIsNearBottom(nearBottom);
    if (!nearBottom) shouldAutoScroll.current = false;
    else shouldAutoScroll.current = true;
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!projectId) {
      setLoading(false);
      setMessages([]);
      setError("No se encontró el proyecto para el chat.");
      return;
    }
    if (!token) {
      setLoading(false);
      setMessages([]);
      setError("Debes iniciar sesión para ver el chat del proyecto.");
      return;
    }
    setLoading(true);
    setError(null);
    apiFetch<ChatMessage[]>(`/projects/${projectId}/messages`, {
      token,
      query: { limit: "100" },
    })
      .then((data) => {
        if (Array.isArray(data)) {
          setMessages(data.reverse());
          // Auto-scroll only on initial load
          shouldAutoScroll.current = true;
        } else {
          setMessages([]);
        }
      })
      .catch(() => {
        setMessages([]);
        setError("No se pudo cargar el chat del proyecto.");
      })
      .finally(() => setLoading(false));
  }, [authLoading, projectId, token]);

  // Auto-scroll on new messages (only if near bottom)
  useEffect(() => {
    if (shouldAutoScroll.current && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages]);

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

  const handleSend = async () => {
    if (!input.trim() || !token) return;
    shouldAutoScroll.current = true;
    try {
      const msg = await apiFetch<ChatMessage>(`/projects/${projectId}/messages`, {
        method: "POST",
        token,
        body: { content: input.trim() },
      });
      setMessages((prev) => [...prev, msg]);
      setInput("");
    } catch (err) {
      toast.error("Failed to send message");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleDelete = async (msgId: string, senderId: string) => {
    if (!token || !userId) return;
    if (String(senderId) !== String(userId)) return;
    try {
      await apiFetch(`/projects/${projectId}/messages/${msgId}`, {
        method: "DELETE",
        token,
      });
      setMessages((prev) => prev.filter((m) => m.id !== msgId));
    } catch (err) {
      toast.error("Failed to delete message");
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 p-8">
        <div className="space-y-3 w-full max-w-md">
          {[1, 2, 3].map((i) => (
            <div key={i} className={`flex ${i % 2 === 0 ? "justify-end" : "justify-start"}`}>
              <div className={`rounded-2xl px-4 py-3 w-3/4 animate-pulse ${
                i % 2 === 0 ? "bg-[hsl(var(--info-muted))]/50 dark:bg-[hsl(var(--info))]/30" : "bg-[hsl(var(--surface-2))] dark:bg-white/5"
              }`}>
                <div className="h-3 rounded bg-current opacity-20 mb-2 w-1/3" />
                <div className="h-3 rounded bg-current opacity-20 w-2/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col flex-1 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21]">
      {error && (
        <div className="mx-4 mt-3 rounded-md border border-[hsl(var(--warning)/25%)] bg-warning-soft p-3 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
          <p className="text-[11px] font-bold uppercase tracking-wide">{error}</p>
        </div>
      )}
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-[hsl(var(--text-secondary))] gap-3">
          <div className="size-16 rounded-2xl bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
            <MessageSquare className="w-8 h-8 opacity-40" />
          </div>
          <p className="text-sm font-medium">No hay mensajes aún</p>
          <p className="text-xs opacity-60">¡Sé el primero en escribir!</p>
        </div>
      ) : (
        <>
          {!isNearBottom && messages.length > 0 && (
            <button
              onClick={() => {
                shouldAutoScroll.current = true;
                scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
              }}
              className="absolute bottom-20 left-1/2 -translate-x-1/2 z-10 px-3 py-1.5 rounded-full bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide shadow-lg hover:scale-105 transition-all"
            >
              Nuevos mensajes ↓
            </button>
          )}
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin"
          >
            {messages.map((msg, idx) => {
              const isOwn = String(msg.sender_id) === String(userId ?? "");
              const showSender = idx === 0 || messages[idx - 1]?.sender_id !== msg.sender_id;
              return (
                <div
                  key={msg.id}
                  className={`flex ${isOwn ? "justify-end" : "justify-start"} ${showSender ? "mt-3" : "mt-0.5"}`}
                >
                  <div
                    className={`relative group max-w-[75%] rounded-2xl px-4 py-2.5 ${
                      isOwn
                        ? "bg-[hsl(var(--primary))] text-white rounded-br-md"
                        : "bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] rounded-bl-md"
                    }`}
                  >
                    {!isOwn && showSender && (
                      <p className="text-[11px] font-bold mb-1 opacity-70">
                        {msg.sender_name}
                      </p>
                    )}
                    <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{msg.content}</p>
                    <div className="flex items-center justify-end gap-1.5 mt-1">
                      <span
                        className={`text-[10px] ${
                          isOwn ? "text-[hsl(var(--info))]" : "text-[hsl(var(--text-secondary))]"
                        }`}
                      >
                        {formatMessageTime(msg.created_at)}
                      </span>
                      {isOwn && (
                        <button
                          onClick={() => handleDelete(msg.id, msg.sender_id)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-300"
                          title="Eliminar mensaje"
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
        </>
      )}
      <div className="border-t border-[hsl(var(--border-primary))] dark:border-[hsl(var(--border))] p-3">
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe un mensaje..."
              className="w-full px-4 py-2.5 rounded-xl border border-[hsl(var(--border-primary))] dark:border-[hsl(var(--border))] bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--info)/30%)] focus:border-[hsl(var(--info)/40%)] dark:text-white transition-all pr-10"
            />
            {input.trim() && (
              <button
                onClick={handleSend}
                className="absolute right-1.5 bottom-1.5 p-1.5 rounded-lg bg-[hsl(var(--primary))] text-white hover:opacity-90 transition-opacity"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
        <p className="text-[10px] text-[hsl(var(--text-secondary))] text-center mt-1.5 opacity-50">
          Enter para enviar · Shift+Enter para salto de línea
        </p>
      </div>
    </div>
  );
}
