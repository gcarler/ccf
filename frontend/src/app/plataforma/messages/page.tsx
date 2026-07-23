"use client";

import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useWorkspaceSocket } from "@/hooks/useWorkspaceSocket";
import { apiFetch } from "@/lib/http";
import type { ConversationRead,DirectMessageItem, WsEvent } from "@/types/directMessages";
import clsx from "clsx";
import {
ChevronLeft,
Circle,
Loader2,
MessageCircle,
Plus,
Search,
Send,
UserPlus
} from "lucide-react";
import React,{ useCallback,useEffect,useRef,useState } from "react";

/** Strip HTML tags for defense-in-depth (React already escapes JSX by default) */
function sanitizeText(text: string): string {
    return text.replace(/<[^>]*>/g, "");
}

interface SearchedUser {
    id: string;
    username: string;
    email: string;
    avatar_url: string | null;
}

function AvatarInitial({ name, size = "md" }: { name: string; size?: "sm" | "md" }) {
    const safeName = (name || "U").slice(0, 2).toUpperCase();
    const initials = safeName;
    const colors = [
        "from-[hsl(var(--info))] to-[hsl(var(--info))]",
        "from-[hsl(var(--domain-cyan))] to-[hsl(var(--domain-cyan))]",
        "from-[hsl(var(--success))] to-[hsl(var(--success))]",
        "from-[hsl(var(--danger))] to-[hsl(var(--danger))]",
        "from-[hsl(var(--warning))] to-[hsl(var(--warning))]",
    ];
    const color = colors[name.charCodeAt(0) % colors.length];
    return (
        <div className={clsx(
            "rounded-lg bg-gradient-to-br flex items-center justify-center text-white font-bold shrink-0",
            color,
            size === "sm" ? "size-7 text-[9px]" : "size-8 text-[10px]"
        )}>
            {initials}
        </div>
    );
}

export default function MessagesPage() {
    const { token, user } = useAuth();
    const { addToast } = useToast();
    const [conversations, setConversations] = useState<ConversationRead[]>([]);
    const [activeConv, setActiveConv] = useState<ConversationRead | null>(null);
    const [messages, setMessages] = useState<DirectMessageItem[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(true);
    const [loadingMessages, setLoadingMessages] = useState(false);
    const [sending, setSending] = useState(false);
    const [conversationFilter, setConversationFilter] = useState("");
    const scrollRef = useRef<HTMLDivElement>(null);
    const userId = user?.id ? String(user.id) : "";
    const inputRef = useRef<HTMLInputElement>(null);
    const messagesRef = useRef<DirectMessageItem[]>([]);
    const activeConvIdRef = useRef<string | null>(null);

    // ── New conversation drawer ──────────────────────────────────────────
    const [showNewConvDrawer, setShowNewConvDrawer] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<SearchedUser[]>([]);
    const [searching, setSearching] = useState(false);
    const [creatingConv, setCreatingConv] = useState(false);
    const [searchError, setSearchError] = useState("");
    const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);

    // Keep refs in sync with state for stale-closure prevention
    messagesRef.current = messages;
    activeConvIdRef.current = activeConv?.id ?? null;

    const loadConversations = useCallback(() => {
        if (!token) { setLoading(false); return; }
        apiFetch<ConversationRead[]>("/chat/conversations", { token })
            .then((data) => { if (Array.isArray(data)) setConversations(data); })
            .catch(() => { addToast("Error al cargar conversaciones", "error"); })
            .finally(() => setLoading(false));
    }, [token, addToast]);

    useEffect(() => { loadConversations(); }, [loadConversations]);

    useEffect(() => {
        const convId = activeConv?.id;
        if (!token || !convId) return;
        const controller = new AbortController();
        setMessages([]);
        setLoadingMessages(true);
        apiFetch<DirectMessageItem[]>(
            `/chat/conversations/${convId}/messages`,
            { token, query: { limit: "100" }, signal: controller.signal }
        ).then((data) => { if (Array.isArray(data)) setMessages(data.reverse()); })
        .catch((err) => { if (err?.name !== "AbortError") addToast("Error al cargar mensajes", "error"); })
        .finally(() => { if (!controller.signal.aborted) setLoadingMessages(false); });
        apiFetch(`/chat/conversations/${convId}/read`, { method: "POST", token, signal: controller.signal })
            .catch(() => { addToast("No se pudo marcar como leído", "error"); });
        return () => controller.abort();
    }, [activeConv?.id, token, addToast]);

    const loadOlderMessages = useCallback(async () => {
        const convId = activeConv?.id;
        if (!token || !convId || loadingMessages || messagesRef.current.length === 0) return;
        setLoadingMessages(true);
        try {
            const oldest = messagesRef.current[0];
            const older = await apiFetch<DirectMessageItem[]>(
                `/chat/conversations/${convId}/messages`,
                { token, query: { limit: "50", before: oldest.created_at } }
            );
            if (Array.isArray(older) && older.length > 0) {
                setMessages((prev) => [...older.reverse(), ...prev]);
            }
        } catch { /* silent */ }
        finally { setLoadingMessages(false); }
    }, [token, activeConv?.id, loadingMessages]);

    const handleSocketEvent = useCallback((payload: WsEvent) => {
        if (payload.event === "direct_message" && "conversation_id" in payload && "message" in payload) {
            const evt = payload as import("@/types/directMessages").WsDirectMessageEvent;
            const currentActiveId = activeConvIdRef.current;
            if (evt.conversation_id === currentActiveId) {
                setMessages((prev) => [...prev, evt.message]);
                setConversations((prev) => prev.map((c) =>
                    c.id === currentActiveId
                        ? { ...c, last_message_content: evt.message.content, last_message_at: evt.message.created_at, last_sender_id: evt.message.sender_id, unread_count: 0 }
                        : c
                ));
            } else {
                setConversations((prev) => prev.map((c) =>
                    c.id === evt.conversation_id
                        ? { ...c, last_message_content: evt.message.content, last_message_at: evt.message.created_at, last_sender_id: evt.message.sender_id, unread_count: (c.unread_count ?? 0) + 1 }
                        : c
                ));
            }
        }
    }, []);

    const { status: wsStatus } = useWorkspaceSocket({ rooms: activeConv ? [`dm_${activeConv.id}`] : [], enabled: !!token && !!activeConv, onEvent: handleSocketEvent });

    useEffect(() => {
        if (scrollRef.current) {
            const el = scrollRef.current;
            const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150;
            if (isNearBottom) el.scrollTop = el.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || !token || !activeConv || sending) return;
        const content = input.trim();
        setInput("");
        setSending(true);
        try {
            const msg = await apiFetch<DirectMessageItem>(
                `/chat/conversations/${activeConv.id}/messages`,
                { method: "POST", token, body: { content } }
            );
            setMessages((prev) => [...prev, msg]);
        } catch {
            setInput(content);
            addToast("Error al enviar mensaje", "error");
        } finally {
            setSending(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const getOtherParticipant = (conv: ConversationRead) =>
        conv.participants.find((p) => p.persona_id !== userId);

    const filteredConversations = conversationFilter.trim()
        ? conversations.filter((c) => {
            const other = getOtherParticipant(c);
            const name = (other?.username || "").toLowerCase();
            return name.includes(conversationFilter.toLowerCase());
          })
        : conversations;

    const handleSearchChange = (value: string) => {
        setSearchQuery(value);
        setSearchError("");
        if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
        if (value.trim().length < 2) { setSearchResults([]); return; }
        searchTimeoutRef.current = setTimeout(async () => {
            if (!token) return;
            setSearching(true);
            try {
                const results = await apiFetch<SearchedUser[]>(`/chat/users/search?q=${encodeURIComponent(value.trim())}`, { token });
                setSearchResults(Array.isArray(results) ? results : []);
                if (Array.isArray(results) && results.length === 0) setSearchError("No se encontraron usuarios");
            } catch {
                setSearchError("Error al buscar usuarios");
                setSearchResults([]);
            } finally { setSearching(false); }
        }, 300);
    };

    useEffect(() => {
        return () => { if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current); };
    }, []);

    const handleCreateConversation = async (participantId: string) => {
        if (!token) return;
        setCreatingConv(true);
        try {
            const conv = await apiFetch<ConversationRead>("/chat/conversations", {
                method: "POST", token, body: { participant_ids: [participantId] },
            });
            setConversations((prev) => {
                const exists = prev.some((c) => c.id === conv.id);
                return exists ? prev : [conv, ...prev];
            });
            setActiveConv(conv);
            setShowNewConvDrawer(false);
            setSearchQuery("");
            setSearchResults([]);
            setTimeout(() => inputRef.current?.focus(), 200);
        } catch { setSearchError("Error al crear la conversación"); }
        finally { setCreatingConv(false); }
    };

    const openNewConvDrawer = () => {
        setShowNewConvDrawer(true);
        setSearchQuery("");
        setSearchResults([]);
        setSearchError("");
        setTimeout(() => searchInputRef.current?.focus(), 200);
    };

    const selectConversation = (conv: ConversationRead) => {
        setActiveConv(conv);
    };

    const totalUnread = conversations.reduce((sum, c) => sum + (c.unread_count || 0), 0);

    // ── Conversation sidebar ─────────────────────────────────────────────
    const conversationSidebar = (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]/30 dark:bg-[#1a1b1d] border-r border-[hsl(var(--border))] dark:border-white/[0.05]">
            {/* Header */}
            <div className="h-10 px-3 flex items-center justify-between shrink-0 border-b border-[hsl(var(--border))] dark:border-white/[0.05] bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
                <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                        <MessageCircle size={12} />
                        <span className="hidden xs:inline">Mensajes</span>
                    </span>
                    {totalUnread > 0 && (
                        <span className="inline-flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-[hsl(var(--danger))] text-white text-[9px] font-bold">
                            {totalUnread}
                        </span>
                    )}
                </div>
                <button
                    onClick={openNewConvDrawer}
                    className="size-6 rounded-md flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all"
                    aria-label="Nueva conversación"
                    title="Nueva conversación"
                >
                    <Plus size={13} />
                </button>
            </div>

            {/* Search */}
            <div className="px-2 py-2 shrink-0">
                <div className="relative">
                    <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                    <input
                        type="text"
                        value={conversationFilter}
                        onChange={(e) => setConversationFilter(e.target.value)}
                        placeholder="Buscar..."
                        aria-label="Buscar conversaciones"
                        className="w-full pl-7 pr-3 py-1.5 text-[11px] bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))]"
                    />
                </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto scrollbar-thin px-1">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-10 gap-2 text-[hsl(var(--text-secondary))]">
                        <Loader2 size={16} className="animate-spin" />
                        <p className="text-[11px]">Cargando...</p>
                    </div>
                ) : filteredConversations.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-10 gap-3 px-3 text-center">
                        <div className="size-10 rounded-xl bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                            <MessageCircle size={18} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
                        </div>
                        <p className="text-[11px] font-semibold text-[hsl(var(--text-secondary))]">
                            {conversationFilter ? "Sin resultados" : "Sin conversaciones"}
                        </p>
                        {!conversationFilter && (
                            <button
                                onClick={openNewConvDrawer}
                                aria-label="Iniciar nueva conversación"
                                className="flex items-center gap-1.5 text-[11px] font-semibold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors"
                            >
                                <UserPlus size={12} /> Iniciar chat
                            </button>
                        )}
                    </div>
                ) : (
                    filteredConversations.map((conv) => {
                        const other = getOtherParticipant(conv);
                        const isActive = activeConv?.id === conv.id;
                        return (
                            <button
                                key={conv.id}
                                onClick={() => selectConversation(conv)}
                                aria-label={`Abrir conversación con ${other?.username || "Usuario"}`}
                                className={clsx(
                                    "w-full text-left flex items-center gap-2.5 px-2 py-2 rounded-lg transition-all group mb-0.5",
                                    isActive
                                        ? "bg-info-soft dark:bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))]"
                                        : "hover:bg-[hsl(var(--surface-2))]/60 dark:hover:bg-white/[0.04]"
                                )}
                            >
                                <AvatarInitial name={other?.username || "U"} size="sm" />
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-1">
                                        <p className={clsx(
                                            "text-[12px] font-semibold truncate",
                                            isActive ? "text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" : "text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
                                        )}>
                                            {other?.username || "Usuario"}
                                        </p>
                                        {conv.last_message_at && (
                                            <span className="text-[9px] text-[hsl(var(--text-secondary))] shrink-0">
                                                {new Date(conv.last_message_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-1.5 mt-0.5">
                                        <p className="text-[11px] text-[hsl(var(--text-secondary))] truncate flex-1">
                                            {conv.last_message_content || "Sin mensajes"}
                                        </p>
                                        {conv.unread_count > 0 && (
                                            <span className="inline-flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-[hsl(var(--primary))] text-white text-[9px] font-bold shrink-0">
                                                {conv.unread_count}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </button>
                        );
                    })
                )}
            </div>
        </div>
    );

    return (
        <WorkspaceLayout
            sidebarTitle="Mensajes"
            customSidebar={conversationSidebar}
            sidebarSections={[]}
        >
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
                {!activeConv ? (
                    /* ── Empty state ── */
                    <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center p-6">
                        <div className="size-14 rounded-2xl bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                            <MessageCircle size={26} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Selecciona una conversación</p>
                            <p className="text-[12px] text-[hsl(var(--text-secondary))] mt-1">o empieza una nueva desde el panel izquierdo</p>
                        </div>
                        <button
                            onClick={openNewConvDrawer}
                            aria-label="Crear nueva conversación"
                            className="flex items-center gap-2 px-4 py-2 text-[11px] font-bold uppercase tracking-wide bg-[hsl(var(--primary))] text-white rounded-lg hover:bg-[hsl(var(--primary))] active:scale-95 transition-all shadow-sm shadow-[hsl(var(--info)/20%)] mt-1"
                        >
                            <Plus size={13} /> Nueva conversación
                        </button>
                    </div>
                ) : (
                    <>
                        {/* ── Thread header ── */}
                        <div className="h-10 px-3 md:px-4 flex items-center gap-3 shrink-0 border-b border-[hsl(var(--border))] dark:border-white/[0.05] bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
                            <button
                                className="p-1 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] transition-all"
                                aria-label="Volver a conversaciones"
                                title="Volver a conversaciones"
                                onClick={() => setActiveConv(null)}
                            >
                                <ChevronLeft size={15} />
                            </button>
                            <AvatarInitial name={getOtherParticipant(activeConv)?.username || "U"} />
                            <div className="flex-1 min-w-0">
                                <p className="text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">
                                    {getOtherParticipant(activeConv)?.username || "Usuario"}
                                </p>
                                <div className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-secondary))]">
                                    {wsStatus === "open" ? (
                                        <>
                                            <Circle size={7} className="fill-[hsl(var(--success))] text-[hsl(var(--success))]" />
                                            <span className="hidden xs:inline">Activo</span>
                                        </>
                                    ) : wsStatus === "error" ? (
                                        <>
                                            <Circle size={7} className="fill-red-400 text-red-400" />
                                            <span className="hidden xs:inline">Desconectado</span>
                                        </>
                                    ) : (
                                        <>
                                            <Circle size={7} className="fill-[hsl(var(--warning))] text-[hsl(var(--warning))]" />
                                            <span className="hidden xs:inline">Conectando...</span>
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* ── Messages ── */}
                        <div
                            ref={scrollRef}
                            onScroll={(e) => {
                                const el = e.currentTarget;
                                if (el.scrollTop < 60) loadOlderMessages();
                            }}
                            className="flex-1 overflow-y-auto scrollbar-thin p-3 md:p-4 space-y-3 bg-[hsl(var(--surface-1))]/30 dark:bg-[#111213]"
                        >
                            {loadingMessages ? (
                                <div className="flex flex-col items-center justify-center h-full gap-3 text-[hsl(var(--text-secondary))]">
                                    <Loader2 size={20} className="animate-spin" />
                                    <p className="text-[12px]">Cargando mensajes...</p>
                                </div>
                            ) : messages.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full gap-3 text-[hsl(var(--text-secondary))]">
                                    <div className="size-10 rounded-xl bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                                        <MessageCircle size={18} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
                                    </div>
                                    <p className="text-[12px] font-semibold text-[hsl(var(--text-secondary))]">Sin mensajes aún</p>
                                    <p className="text-[11px] text-[hsl(var(--text-secondary))]">Sé el primero en escribir</p>
                                </div>
                            ) : (
                                messages.map((msg) => {
                                    const isOwn = msg.sender_id === userId;
                                    return (
                                        <div
                                            key={msg.id}
                                            className={clsx("flex", isOwn ? "justify-end" : "justify-start")}
                                        >
                                            {!isOwn && (
                                                <div className="mr-2 mt-1 shrink-0 hidden xs:block">
                                                    <AvatarInitial name={msg.sender_name || "U"} size="sm" />
                                                </div>
                                            )}
                                            <div className={clsx("space-y-0.5", isOwn ? "max-w-[80%] md:max-w-[68%]" : "max-w-[85%] md:max-w-[68%]")}>
                                                {!isOwn && (
                                                    <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] px-1">
                                                        {msg.sender_name}
                                                    </p>
                                                )}
                                                <div className={clsx(
                                                    "px-3 md:px-3.5 py-2 rounded-2xl text-[13px] md:text-sm leading-relaxed",
                                                    isOwn
                                                        ? "bg-[hsl(var(--primary))] text-white rounded-br-md"
                                                        : "bg-[hsl(var(--bg-primary))] dark:bg-white/[0.07] border border-[hsl(var(--border))] dark:border-white/[0.06] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] rounded-bl-md shadow-sm"
                                                )}>
                                                    <p className="whitespace-pre-wrap break-words">{sanitizeText(msg.content)}</p>
                                                </div>
                                                <div className={clsx("flex items-center gap-1", isOwn ? "justify-end pr-1" : "pl-1")}>
                                                    <span className={clsx(
                                                        "text-[10px]",
                                                        isOwn ? "text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]"
                                                    )}>
                                                        {new Date(msg.created_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                                                    </span>
                                                    {isOwn && (
                                                        <span className="text-[10px] text-[hsl(var(--primary))]">{msg.is_read ? "✓✓" : "✓"}</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                        </div>

                        {/* ── Input bar ── */}
                        <div className="border-t border-[hsl(var(--border))] dark:border-white/[0.05] p-2 md:p-3 bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
                            <div className="flex items-center gap-2">
                                <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-[hsl(var(--surface-1))] dark:bg-white/[0.05] border border-[hsl(var(--border))] dark:border-white/10 rounded-xl focus-within:ring-2 focus-within:ring-[hsl(var(--primary))]/20 transition-all">
                                    <input
                                        ref={inputRef}
                                        type="text"
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        disabled={sending}
                                        placeholder="Escribe un mensaje..."
                                        aria-label="Escribe un mensaje"
                                        className="flex-1 text-sm bg-transparent outline-none text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] min-w-0 disabled:opacity-50"
                                    />
                                </div>
                                <button
                                    onClick={handleSend}
                                    disabled={!input.trim() || sending}
                                    aria-label="Enviar mensaje"
                                    className="size-9 rounded-xl bg-[hsl(var(--primary))] text-white flex items-center justify-center hover:bg-[hsl(var(--primary))] disabled:opacity-30 disabled:cursor-not-allowed active:scale-95 transition-all shadow-sm shadow-[hsl(var(--info)/20%)] shrink-0"
                                >
                                    {sending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>

            {/* ── New Conversation Drawer ─────────────────────────────────── */}
            <WorkspaceDrawer
                isOpen={showNewConvDrawer}
                onClose={() => {
                    if (!creatingConv) {
                        setShowNewConvDrawer(false);
                        setSearchQuery("");
                        setSearchResults([]);
                    }
                }}
                title="Nueva conversación"
                subtitle="Busca un usuario para iniciar un chat"
            >
                <div className="space-y-4">
                    {/* Search input */}
                    <div className="relative">
                        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        <input
                            ref={searchInputRef}
                            type="text"
                            value={searchQuery}
                            onChange={(e) => handleSearchChange(e.target.value)}
                            placeholder="Buscar por nombre o email..."
                            aria-label="Buscar usuario para nueva conversación"
                            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-sm outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:text-white"
                            autoComplete="off"
                        />
                    </div>

                    {/* Results */}
                    <div className="space-y-1">
                        {searching ? (
                            <div className="flex items-center justify-center py-8 text-[hsl(var(--text-secondary))] gap-2">
                                <Loader2 size={15} className="animate-spin" />
                                <span className="text-sm">Buscando...</span>
                            </div>
                        ) : searchError ? (
                            <p className="text-center py-8 text-sm text-[hsl(var(--text-secondary))]">{searchError}</p>
                        ) : searchResults.length > 0 ? (
                            searchResults.map((u) => (
                                <button
                                    key={u.id}
                                    onClick={() => handleCreateConversation(String(u.id))}
                                    disabled={creatingConv}
                                    aria-label={`Iniciar conversación con ${u.username}`}
                                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors disabled:opacity-50 text-left"
                                >
                                    <AvatarInitial name={u.username} />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">{u.username}</p>
                                        <p className="text-[11px] text-[hsl(var(--text-secondary))] truncate">{u.email}</p>
                                    </div>
                                    {creatingConv && <Loader2 size={14} className="animate-spin text-[hsl(var(--primary))] shrink-0" />}
                                </button>
                            ))
                        ) : (
                            <div className="flex flex-col items-center justify-center py-8 text-[hsl(var(--text-secondary))] gap-2">
                                <Search size={24} className="opacity-20" />
                                <p className="text-sm">{searchQuery.trim().length >= 2 ? "Sin resultados" : "Escribe para buscar"}</p>
                                {searchQuery.trim().length < 2 && <p className="text-[11px]">Mínimo 2 caracteres</p>}
                            </div>
                        )}
                    </div>
                </div>
            </WorkspaceDrawer>
        </WorkspaceLayout>
    );
}
