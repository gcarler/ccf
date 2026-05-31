"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { useWorkspaceSocket } from "@/hooks/useWorkspaceSocket";
import {
    MessageCircle, Send, Plus, ChevronLeft,
    Search, X, Loader2, UserPlus, Circle,
} from "lucide-react";
import type { ConversationRead, DirectMessageItem } from "@/types/directMessages";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import clsx from "clsx";

interface SearchedUser {
    id: number;
    username: string;
    email: string;
    avatar_url: string | null;
}

function AvatarInitial({ name, size = "md" }: { name: string; size?: "sm" | "md" }) {
    const initials = name.slice(0, 2).toUpperCase();
    const colors = [
        "from-blue-500 to-blue-700",
        "from-violet-500 to-violet-700",
        "from-emerald-500 to-emerald-700",
        "from-rose-500 to-rose-700",
        "from-amber-500 to-amber-700",
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
    const [conversations, setConversations] = useState<ConversationRead[]>([]);
    const [activeConv, setActiveConv] = useState<ConversationRead | null>(null);
    const [messages, setMessages] = useState<DirectMessageItem[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(true);
    const [loadingMessages, setLoadingMessages] = useState(false);
    const [conversationFilter, setConversationFilter] = useState("");
    const scrollRef = useRef<HTMLDivElement>(null);
    const userId = user?.id;
    const inputRef = useRef<HTMLInputElement>(null);

    // ── New conversation modal ──────────────────────────────────────────
    const [showNewConvModal, setShowNewConvModal] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<SearchedUser[]>([]);
    const [searching, setSearching] = useState(false);
    const [creatingConv, setCreatingConv] = useState(false);
    const [searchError, setSearchError] = useState("");
    const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);

    const loadConversations = useCallback(() => {
        if (!token) return;
        apiFetch<ConversationRead[]>("/chat/conversations", { token })
            .then((data) => { if (Array.isArray(data)) setConversations(data); })
            .catch(() => {})
            .finally(() => setLoading(false));
    }, [token]);

    useEffect(() => { loadConversations(); }, [loadConversations]);

    useEffect(() => {
        if (!token || !activeConv) return;
        setMessages([]);
        setLoadingMessages(true);
        apiFetch<DirectMessageItem[]>(
            `/chat/conversations/${activeConv.id}/messages`,
            { token, query: { limit: "100" } }
        ).then((data) => { if (Array.isArray(data)) setMessages(data.reverse()); })
        .catch(() => {})
        .finally(() => setLoadingMessages(false));
        apiFetch(`/chat/conversations/${activeConv.id}/read`, { method: "POST", token }).catch(() => {});
    }, [activeConv?.id, token]);

    const handleSocketEvent = useCallback((payload: any) => {
        if (payload?.event === "direct_message" && payload?.conversation_id === activeConv?.id) {
            setMessages((prev) => [...prev, payload.message]);
            setConversations((prev) => prev.map((c) =>
                c.id === activeConv?.id
                    ? { ...c, last_message_content: payload.message.content, last_message_at: payload.message.created_at, last_sender_id: payload.message.sender_id, unread_count: 0 }
                    : c
            ));
        } else if (payload?.event === "direct_message") {
            setConversations((prev) => prev.map((c) =>
                c.id === payload.conversation_id
                    ? { ...c, last_message_content: payload.message.content, last_message_at: payload.message.created_at, last_sender_id: payload.message.sender_id }
                    : c
            ));
        }
    }, [activeConv?.id]);

    useWorkspaceSocket({ rooms: activeConv ? [`dm_${activeConv.id}`] : [], enabled: !!token && !!activeConv, onEvent: handleSocketEvent });

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || !token || !activeConv) return;
        const content = input.trim();
        setInput("");
        try {
            const msg = await apiFetch<DirectMessageItem>(
                `/chat/conversations/${activeConv.id}/messages`,
                { method: "POST", token, body: { content } }
            );
            setMessages((prev) => [...prev, msg]);
        } catch {
            setInput(content);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const getOtherParticipant = (conv: ConversationRead) =>
        conv.participants.find((p) => p.user_id !== userId);

    // Filtered conversations for search bar
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

    // Cleanup search timeout on unmount
    useEffect(() => {
        return () => { if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current); };
    }, []);

    const handleCreateConversation = async (participantId: number) => {
        if (!token) return;
        setCreatingConv(true);
        try {
            const conv = await apiFetch<ConversationRead>("/chat/conversations", {
                method: "POST", token, body: { participant_ids: [participantId] },
            });
            await loadConversations();
            setActiveConv(conv);
            setShowNewConvModal(false);
            setSearchQuery("");
            setSearchResults([]);
            setTimeout(() => inputRef.current?.focus(), 100);
        } catch { setSearchError("Error al crear la conversación"); }
        finally { setCreatingConv(false); }
    };

    const openNewConvModal = () => {
        setShowNewConvModal(true);
        setSearchQuery("");
        setSearchResults([]);
        setSearchError("");
        setTimeout(() => searchInputRef.current?.focus(), 100);
    };

    const totalUnread = conversations.reduce((sum, c) => sum + (c.unread_count || 0), 0);

    // ── Conversation sidebar (passed as customSidebar to WorkspaceLayout) ──
    const conversationSidebar = (
        <div className="flex flex-col h-full bg-slate-50/30 dark:bg-[#1a1b1d] border-r border-slate-100 dark:border-white/[0.05]">
            {/* Header */}
            <div className="h-10 px-3 flex items-center justify-between shrink-0 border-b border-slate-100 dark:border-white/[0.05] bg-white dark:bg-[#141517]">
                <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300 flex items-center gap-1.5">
                        <MessageCircle size={12} />
                        Mensajes
                    </span>
                    {totalUnread > 0 && (
                        <span className="inline-flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-rose-500 text-white text-[9px] font-bold">
                            {totalUnread}
                        </span>
                    )}
                </div>
                <button
                    onClick={openNewConvModal}
                    className="size-6 rounded-md flex items-center justify-center text-slate-400 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
                    title="Nueva conversación"
                >
                    <Plus size={13} />
                </button>
            </div>

            {/* Search bar */}
            <div className="px-2 py-2 shrink-0">
                <div className="relative">
                    <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                        type="text"
                        value={conversationFilter}
                        onChange={(e) => setConversationFilter(e.target.value)}
                        placeholder="Buscar conversación..."
                        className="w-full pl-7 pr-3 py-1.5 text-[11px] bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-700 dark:text-slate-300 placeholder:text-slate-400"
                    />
                </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto scrollbar-thin px-1">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-10 gap-2 text-slate-400">
                        <Loader2 size={16} className="animate-spin" />
                        <p className="text-[11px]">Cargando...</p>
                    </div>
                ) : filteredConversations.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-10 gap-3 px-3 text-center">
                        <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                            <MessageCircle size={18} className="text-slate-300 dark:text-slate-600" />
                        </div>
                        <p className="text-[11px] font-semibold text-slate-500">Sin conversaciones</p>
                        <button
                            onClick={openNewConvModal}
                            className="flex items-center gap-1.5 text-[11px] font-semibold text-blue-500 hover:text-blue-600 transition-colors"
                        >
                            <UserPlus size={12} /> Iniciar chat
                        </button>
                    </div>
                ) : (
                    filteredConversations.map((conv) => {
                        const other = getOtherParticipant(conv);
                        const isActive = activeConv?.id === conv.id;
                        return (
                            <button
                                key={conv.id}
                                onClick={() => setActiveConv(conv)}
                                className={clsx(
                                    "w-full text-left flex items-center gap-2.5 px-2 py-2 rounded-lg transition-all group mb-0.5",
                                    isActive
                                        ? "bg-blue-50 dark:bg-blue-500/10 text-blue-600"
                                        : "hover:bg-slate-100/60 dark:hover:bg-white/[0.04]"
                                )}
                            >
                                <AvatarInitial name={other?.username || "U"} size="sm" />
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-1">
                                        <p className={clsx(
                                            "text-[12px] font-semibold truncate",
                                            isActive ? "text-blue-700 dark:text-blue-400" : "text-slate-800 dark:text-slate-200"
                                        )}>
                                            {other?.username || "Usuario"}
                                        </p>
                                        {conv.unread_count > 0 && (
                                            <span className="shrink-0 h-4 min-w-[16px] px-1 rounded-full bg-blue-500 text-white text-[9px] font-bold flex items-center justify-center">
                                                {conv.unread_count}
                                            </span>
                                        )}
                                    </div>
                                    {conv.last_message_content && (
                                        <p className="text-[10px] text-slate-400 dark:text-slate-500 truncate mt-0.5">
                                            {conv.last_message_content}
                                        </p>
                                    )}
                                </div>
                            </button>
                        );
                    })
                )}
            </div>
        </div>
    );

    // ── Render ────────────────────────────────────────────────────────────
    return (
        <WorkspaceLayout
            breadcrumbs={[{ label: "Mensajes", icon: MessageCircle }]}
            allowedPermissions={["messaging:read"]}
            customSidebar={conversationSidebar}
            rightActions={
                <button
                    onClick={openNewConvModal}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide bg-blue-600 text-white rounded-md hover:bg-blue-700 active:scale-95 transition-all shadow-sm shadow-blue-500/20"
                >
                    <Plus size={13} /> Nuevo mensaje
                </button>
            }
        >
            <div className="flex flex-col h-full bg-white dark:bg-[#141517]">
                {!activeConv ? (
                    /* ── Empty state ── */
                    <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center p-6">
                        <div className="size-14 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                            <MessageCircle size={26} className="text-slate-300 dark:text-slate-600" />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-slate-600 dark:text-slate-400">Selecciona una conversación</p>
                            <p className="text-[12px] text-slate-400 mt-1">o empieza una nueva desde el panel izquierdo</p>
                        </div>
                        <button
                            onClick={openNewConvModal}
                            className="flex items-center gap-2 px-4 py-2 text-[11px] font-bold uppercase tracking-wide bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:scale-95 transition-all shadow-sm shadow-blue-500/20 mt-1"
                        >
                            <Plus size={13} /> Nueva conversación
                        </button>
                    </div>
                ) : (
                    <>
                        {/* ── Thread header ── */}
                        <div className="h-10 px-4 flex items-center gap-3 shrink-0 border-b border-slate-100 dark:border-white/[0.05] bg-white dark:bg-[#141517]">
                            <button
                                onClick={() => setActiveConv(null)}
                                className="md:hidden p-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md text-slate-400 transition-all"
                            >
                                <ChevronLeft size={15} />
                            </button>
                            <AvatarInitial name={getOtherParticipant(activeConv)?.username || "U"} />
                            <div className="flex-1 min-w-0">
                                <p className="text-[12px] font-bold text-slate-800 dark:text-slate-100 truncate">
                                    {getOtherParticipant(activeConv)?.username || "Usuario"}
                                </p>
                                <div className="flex items-center gap-1 text-[10px] text-slate-400">
                                    <Circle size={7} className="fill-emerald-400 text-emerald-400" />
                                    Activo
                                </div>
                            </div>
                        </div>

                        {/* ── Messages ── */}
                        <div
                            ref={scrollRef}
                            className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-3 bg-slate-50/30 dark:bg-[#111213]"
                        >
                            {loadingMessages ? (
                                <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-400">
                                    <Loader2 size={20} className="animate-spin" />
                                    <p className="text-[12px]">Cargando mensajes...</p>
                                </div>
                            ) : messages.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-400">
                                    <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                                        <MessageCircle size={18} className="text-slate-300 dark:text-slate-600" />
                                    </div>
                                    <p className="text-[12px] font-semibold text-slate-500">Sin mensajes aún</p>
                                    <p className="text-[11px] text-slate-400">Sé el primero en escribir</p>
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
                                                <div className="mr-2 mt-1 shrink-0">
                                                    <AvatarInitial name={msg.sender_name || "U"} size="sm" />
                                                </div>
                                            )}
                                            <div className="max-w-[68%] space-y-0.5">
                                                {!isOwn && (
                                                    <p className="text-[10px] font-bold text-slate-500 dark:text-slate-400 px-1">
                                                        {msg.sender_name}
                                                    </p>
                                                )}
                                                <div className={clsx(
                                                    "px-3.5 py-2 rounded-2xl text-sm leading-relaxed",
                                                    isOwn
                                                        ? "bg-blue-600 text-white rounded-br-md"
                                                        : "bg-white dark:bg-white/[0.07] border border-slate-100 dark:border-white/[0.06] text-slate-800 dark:text-slate-100 rounded-bl-md shadow-sm"
                                                )}>
                                                    <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                                                </div>
                                                <div className={clsx("flex items-center gap-1", isOwn ? "justify-end pr-1" : "pl-1")}>
                                                    <span className={clsx(
                                                        "text-[10px]",
                                                        isOwn ? "text-blue-400" : "text-slate-400"
                                                    )}>
                                                        {new Date(msg.created_at).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}
                                                    </span>
                                                    {isOwn && (
                                                        <span className="text-[10px] text-blue-400">{msg.is_read ? "✓✓" : "✓"}</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                        </div>

                        {/* ── Input bar ── */}
                        <div className="border-t border-slate-100 dark:border-white/[0.05] p-3 bg-white dark:bg-[#141517]">
                            <div className="flex items-center gap-2">
                                <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-slate-50 dark:bg-white/[0.05] border border-slate-200 dark:border-white/10 rounded-xl focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
                                    <input
                                        ref={inputRef}
                                        type="text"
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        placeholder="Escribe un mensaje..."
                                        className="flex-1 text-sm bg-transparent outline-none text-slate-800 dark:text-slate-100 placeholder:text-slate-400"
                                    />
                                </div>
                                <button
                                    onClick={handleSend}
                                    disabled={!input.trim()}
                                    className="size-9 rounded-xl bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed active:scale-95 transition-all shadow-sm shadow-blue-500/20"
                                >
                                    <Send size={15} />
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>

            {/* ── New Conversation Modal ─────────────────────────────────── */}
            {showNewConvModal && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center">
                    <div
                        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                        onClick={() => { if (!creatingConv) { setShowNewConvModal(false); setSearchQuery(""); setSearchResults([]); } }}
                    />
                    <div className="relative bg-white dark:bg-[#1e1f21] rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-slate-200 dark:border-white/10">
                        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-white/[0.05]">
                            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                                <UserPlus size={15} className="text-blue-500" />
                                Nueva conversación
                            </h3>
                            <button
                                onClick={() => { setShowNewConvModal(false); setSearchQuery(""); setSearchResults([]); }}
                                disabled={creatingConv}
                                className="size-7 flex items-center justify-center rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-40"
                            >
                                <X size={14} />
                            </button>
                        </div>

                        <div className="px-5 pt-4 pb-2">
                            <div className="relative">
                                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    ref={searchInputRef}
                                    type="text"
                                    value={searchQuery}
                                    onChange={(e) => handleSearchChange(e.target.value)}
                                    placeholder="Buscar por nombre o email..."
                                    className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm outline-none focus:ring-2 focus:ring-blue-500/20 dark:text-white"
                                    autoComplete="off"
                                />
                            </div>
                        </div>

                        <div className="max-h-64 overflow-y-auto px-2 pb-3 scrollbar-thin">
                            {searching ? (
                                <div className="flex items-center justify-center py-8 text-slate-400 gap-2">
                                    <Loader2 size={15} className="animate-spin" />
                                    <span className="text-sm">Buscando...</span>
                                </div>
                            ) : searchError ? (
                                <p className="text-center py-8 text-sm text-slate-400">{searchError}</p>
                            ) : searchResults.length > 0 ? (
                                searchResults.map((u) => (
                                    <button
                                        key={u.id}
                                        onClick={() => handleCreateConversation(u.id)}
                                        disabled={creatingConv}
                                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-slate-50 dark:hover:bg-white/5 transition-colors disabled:opacity-50 text-left"
                                    >
                                        <AvatarInitial name={u.username} />
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">{u.username}</p>
                                            <p className="text-[11px] text-slate-400 truncate">{u.email}</p>
                                        </div>
                                        {creatingConv && <Loader2 size={14} className="animate-spin text-blue-500 shrink-0" />}
                                    </button>
                                ))
                            ) : (
                                <div className="flex flex-col items-center justify-center py-8 text-slate-400 gap-2">
                                    <Search size={24} className="opacity-20" />
                                    <p className="text-sm">{searchQuery.trim().length >= 2 ? "Sin resultados" : "Escribe para buscar"}</p>
                                    {searchQuery.trim().length < 2 && <p className="text-[11px]">Mínimo 2 caracteres</p>}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </WorkspaceLayout>
    );
}
