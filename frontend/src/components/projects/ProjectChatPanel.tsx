"use client";

import { useState, useEffect, useRef, useCallback, useMemo, KeyboardEvent } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { useWorkspaceSocket } from "@/hooks/useWorkspaceSocket";
import type { WsEvent } from "@/types/directMessages";
import type { AssigneeCandidate } from "@/types/projects";
import { Send, Trash2, MessageSquare, AtSign } from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";
import ConfirmActionDrawer, { type ConfirmActionState } from "@/components/ConfirmActionDrawer";
import { sortMentionCandidates } from "./utils";

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
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
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
    (payload: WsEvent) => {
      if (payload?.event === "project_message" && "project_id" in payload && "message" in payload && payload.project_id === projectId) {
        const incoming = payload.message as ChatMessage;
        // Dedup: the backend broadcasts the message back to the sender's own
        // client via WS. Since handleSend already added it from the POST
        // response, skip if we already have it (handles both arrival orders).
        if (!incoming?.id) return;
        setMessages((prev) => (prev.some((m) => m.id === incoming.id) ? prev : [...prev, incoming]));
      }
    },
    [projectId]
  );

  useWorkspaceSocket({
    rooms: [`project_${projectId}`],
    enabled: !!token,
    token,
    onEvent: handleSocketEvent,
  });

  // Mentions autocomplete state
  const [mentionState, setMentionState] = useState<{ query: string; start: number } | null>(null);
  const [candidates, setCandidates] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedMentions, setSelectedMentions] = useState<Array<{ id: string; name: string }>>([]);
  const [activeMentionIndex, setActiveMentionIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch candidate mentions when mention query changes
  const mentionQuery = mentionState?.query;
  useEffect(() => {
    if (mentionQuery === undefined) return;
    let active = true;
    const query = mentionQuery.trim();
    const queryParam = `?limit=1000${query ? `&search=${encodeURIComponent(query)}` : ''}`;

    apiFetch<AssigneeCandidate[]>(`/projects/assignee-candidates${queryParam}`, { token: token ?? undefined })
      .catch(() => apiFetch<AssigneeCandidate[]>(`/crm/personas${queryParam}`, { token: token ?? undefined }))
      .then((data) => {
        if (!active) return;
        const list = (Array.isArray(data) ? data : []).map((p) => ({
          id: String(p.user?.id ?? p.id),
          name: p.nombre_completo || [p.first_name, p.last_name].filter(Boolean).join(" ") || p.username || `#${p.id}`,
        }));
        setCandidates(list);
        setActiveMentionIndex(0);
      })
      .catch(() => {
        if (active) setCandidates([]);
      });

    return () => {
      active = false;
    };
  }, [mentionQuery, token]);

  const filteredCandidates = useMemo(() => {
    if (!mentionState) return [];
    return sortMentionCandidates(candidates, mentionState.query);
  }, [candidates, mentionState]);

  const handleSelectMention = (candidate: { id: string; name: string }) => {
    if (!mentionState) return;
    const before = input.slice(0, mentionState.start);
    const after = input.slice(mentionState.start + 1 + mentionState.query.length);
    const next = `${before}@${candidate.name} ${after}`;
    setInput(next);
    setSelectedMentions((prev) => (prev.some((m) => m.id === candidate.id) ? prev : [...prev, candidate]));
    setMentionState(null);
    setTimeout(() => inputRef.current?.focus(), 20);
  };

  const handleInsertAt = () => {
    const inputEl = inputRef.current;
    const current = input;
    const pos = inputEl?.selectionStart ?? current.length;
    const needsSpace = pos > 0 && !current.slice(0, pos).endsWith(' ');
    const insert = needsSpace ? ' @' : '@';
    const next = current.slice(0, pos) + insert + current.slice(pos);
    setInput(next);
    const newPos = pos + insert.length;
    setMentionState({ query: '', start: newPos - 1 });
    setTimeout(() => {
      if (inputEl) {
        inputEl.focus();
        inputEl.setSelectionRange(newPos, newPos);
      }
    }, 20);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInput(val);
    const pos = e.target.selectionStart ?? val.length;
    const before = val.slice(0, pos);
    const lastAt = before.lastIndexOf('@');
    if (lastAt !== -1) {
      const isAtStartOrSpace = lastAt === 0 || /\s/.test(val[lastAt - 1]);
      if (isAtStartOrSpace) {
        const query = before.slice(lastAt + 1);
        if (!query.includes('\n') && query.split(/\s+/).filter(Boolean).length <= 3) {
          setMentionState({ query, start: lastAt });
          return;
        }
      }
    }
    setMentionState(null);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (mentionState && filteredCandidates.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveMentionIndex((prev) => (prev + 1) % filteredCandidates.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveMentionIndex((prev) => (prev - 1 + filteredCandidates.length) % filteredCandidates.length);
        return;
      }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        handleSelectMention(filteredCandidates[activeMentionIndex]);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setMentionState(null);
        return;
      }
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !token) return;
    shouldAutoScroll.current = true;
    try {
      const mentionIds = selectedMentions
        .filter((m) => input.includes(`@${m.name}`))
        .map((m) => m.id);

      const payload: { content: string; mentions?: string[] } = {
        content: input.trim(),
      };
      if (mentionIds.length > 0) {
        payload.mentions = mentionIds;
      }

      const msg = await apiFetch<ChatMessage>(`/projects/${projectId}/messages`, {
        method: "POST",
        token,
        body: payload,
      });
      // Dedup guard (defensive): if the WS broadcast arrived before the POST
      // resolved, the message is already in the list — skip adding it again.
      setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
      setInput("");
      setSelectedMentions([]);
      setMentionState(null);
    } catch (err) {
      toast.error("Failed to send message");
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
      throw new Error("Failed to delete message");
    }
  };

  const requestDelete = (message: ChatMessage) => {
    setConfirmAction({
      title: "Eliminar mensaje",
      description: `¿Confirmas quitar tu mensaje “${message.content}” del historial del chat? Los demás participantes dejarán de verlo.`,
      destructive: true,
      confirmLabel: "Eliminar mensaje",
      onConfirm: () => handleDelete(message.id, message.sender_id),
    });
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 p-8">
        <div className="space-y-3 w-full max-w-md">
          {[1, 2, 3].map((i) => (
            <div key={i} className={`flex ${i % 2 === 0 ? "justify-end" : "justify-start"}`}>
              <div className={`rounded-2xl px-4 py-3 w-3/4 animate-pulse ${
                i % 2 === 0 ? "bg-[hsl(var(--primary)/0.15)]" : "bg-[hsl(var(--surface-2))]"
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
    <div className="relative flex flex-col flex-1 bg-[hsl(var(--surface-1))]">
      {error && (
        <div className="mx-4 mt-3 rounded-md border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-3 text-[hsl(var(--warning))]">
          <p className="text-xs font-bold uppercase tracking-wide">{error}</p>
        </div>
      )}
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-[hsl(var(--muted-foreground))] gap-3">
          <div className="size-16 rounded-2xl bg-[hsl(var(--surface-2))] flex items-center justify-center">
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
              className="absolute bottom-20 left-1/2 -translate-x-1/2 z-10 px-3 py-1.5 rounded-full bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wide shadow-lg hover:scale-105 transition-all"
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
                        ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-br-md"
                        : "bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-bl-md"
                    }`}
                  >
                    {!isOwn && showSender && (
                      <p className="text-xs font-bold mb-1 opacity-70">
                        {msg.sender_name}
                      </p>
                    )}
                    <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">{msg.content}</p>
                    <div className="flex items-center justify-end gap-1.5 mt-1">
                      <span
                        className={`text-2xs ${
                          isOwn ? "text-[hsl(var(--primary-foreground)/0.8)]" : "text-[hsl(var(--muted-foreground))]"
                        }`}
                      >
                        {formatMessageTime(msg.created_at)}
                      </span>
                      {isOwn && (
                        <button
                          type="button"
                          onClick={() => requestDelete(msg)}
                          aria-label={`Eliminar mi mensaje: ${msg.content}`}
                          className="opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-opacity hover:text-[hsl(var(--destructive))]"
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
      <div className="border-t border-[hsl(var(--border))] p-3 relative">
        {mentionState && filteredCandidates.length > 0 && (
          <div
            role="listbox"
            aria-label="Sugerencias de mención"
            data-testid="mention-autocomplete-list"
            className="absolute left-3 right-3 bottom-full mb-1 z-50 max-h-56 overflow-y-auto rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-lg p-1 space-y-0.5"
          >
            {filteredCandidates.slice(0, 50).map((candidate, idx) => (
              <button
                key={candidate.id}
                type="button"
                role="option"
                aria-selected={idx === activeMentionIndex}
                onClick={() => handleSelectMention(candidate)}
                className={clsx(
                  "w-full text-left flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors",
                  idx === activeMentionIndex
                    ? "bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] font-semibold"
                    : "text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]"
                )}
              >
                <span className="size-5 rounded-full bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center justify-center text-2xs font-bold shrink-0">
                  {candidate.name.charAt(0).toUpperCase()}
                </span>
                <span className="truncate">{candidate.name}</span>
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2 items-center">
          <button
            type="button"
            onClick={handleInsertAt}
            aria-label="Mencionar usuario con @"
            title="Mencionar usuario con @"
            className="p-2 rounded-xl text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] transition-colors shrink-0"
          >
            <AtSign className="w-4 h-4" />
          </button>
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Escribe un mensaje... Usa @ para mencionar"
              aria-label="Escribir mensaje en el chat del proyecto"
              className="w-full px-4 py-2.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] transition-all pr-10"
            />
            {input.trim() && (
              <button
                type="button"
                onClick={handleSend}
                aria-label="Enviar mensaje"
                className="absolute right-1.5 bottom-1.5 p-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
        <p className="text-2xs text-[hsl(var(--muted-foreground))] text-center mt-1.5 opacity-50">
          Enter para enviar · Shift+Enter para salto de línea
        </p>
      </div>
      <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
    </div>
  );
}
