"use client";

import WorkspaceLayout from "@/components/WorkspaceLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { ChevronLeft, Circle, MessageCircle, Plus } from "lucide-react";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ConversationSidebar } from "./_components/ConversationSidebar";
import { MessageInput } from "./_components/MessageInput";
import { MessageList } from "./_components/MessageList";
import { NewConversationDrawer } from "./_components/NewConversationDrawer";
import { useChatThread } from "./_hooks/useChatThread";
import { useConversations } from "./_hooks/useConversations";
import { useUserSearch } from "./_hooks/useUserSearch";
import { AvatarInitial } from "@/components/ui/AvatarInitial";
import { apiFetch } from "@/lib/http";
import type { ConversationRead, DirectMessageItem } from "@/types/directMessages";
import clsx from "clsx";

function MessagesPage() {
    const { token, user } = useAuth();
    const { addToast } = useToast();
    const userId = user?.id ? String(user.id) : "";

    const {
        conversations,
        filteredConversations,
        loading: loadingConversations,
        error: conversationsError,
        filter,
        setFilter,
        addConversation,
        updateConversationFromMessage,
        getOtherParticipant,
        totalUnread,
        loadConversations,
    } = useConversations({ token, userPersonaId: userId });

    const searchParams = useSearchParams();
    const initialConvId = searchParams?.get("conv") ?? null;

    const [activeConv, setActiveConv] = useState<ConversationRead | null>(null);
    const [showNewConvDrawer, setShowNewConvDrawer] = useState(false);
    const [creatingConv, setCreatingConv] = useState(false);

    // Open the conversation indicated by ?conv= when the list is loaded.
    useEffect(() => {
        if (!initialConvId || conversations.length === 0) return;
        const match = conversations.find((c) => c.id === initialConvId);
        if (match) setActiveConv(match);
    }, [initialConvId, conversations]);

    const {
        messages,
        loading: loadingMessages,
        sending,
        replyTo,
        setReplyTo,
        loadOlderMessages,
        sendMessage,
        wsStatus,
        hasMoreOlder,
    } = useChatThread({
        token,
        activeConv,
        onMessage: (convId, msg) => {
            const isActive = activeConv?.id === convId;
            updateConversationFromMessage(convId, msg, isActive);
        },
        onError: (context) => {
            const label =
                context === 'load'
                    ? 'No se pudieron cargar los mensajes'
                    : context === 'load_older'
                    ? 'No se pudieron cargar mensajes anteriores'
                    : 'No se pudo actualizar la conversación';
            addToast(label, 'error');
        },
    });

    const userSearch = useUserSearch({ token, debounceMs: 300, minLength: 2 });

    const handleSelectConversation = useCallback((conv: ConversationRead) => {
        setActiveConv(conv);
    }, []);

    const handleNewConversation = useCallback(() => {
        setShowNewConvDrawer(true);
        userSearch.reset();
    }, [userSearch]);

    const handleCreateConversation = useCallback(
        async (participantId: string) => {
            if (!token) return;
            setCreatingConv(true);
            try {
                const conv = await apiFetch<ConversationRead>("/chat/conversations", {
                    method: "POST",
                    token,
                    body: { participant_ids: [participantId] },
                });
                addConversation(conv);
                setActiveConv(conv);
                setShowNewConvDrawer(false);
                userSearch.reset();
            } catch {
                addToast("Error al crear la conversación", "error");
            } finally {
                setCreatingConv(false);
            }
        },
        [token, addConversation, userSearch, addToast]
    );

    const handleSend = useCallback(
        async (content: string, opts: { attachment?: File; replyTo?: DirectMessageItem; mentions: string[] }) => {
            if (!activeConv) return { error: "send" as const };
            const result = await sendMessage(content, opts);
            if (result.error === "upload") addToast("Error al subir archivo", "error");
            if (result.error === "send") addToast("Error al enviar mensaje", "error");
            return result;
        },
        [activeConv, sendMessage, addToast]
    );

    const conversationSidebar = (
        <ConversationSidebar
            conversations={conversations}
            filteredConversations={filteredConversations}
            loading={loadingConversations}
            error={conversationsError}
            onRetry={loadConversations}
            filter={filter}
            onFilterChange={setFilter}
            activeConvId={activeConv?.id ?? null}
            onSelectConv={handleSelectConversation}
            onNewConv={handleNewConversation}
            totalUnread={totalUnread}
            getOtherParticipant={getOtherParticipant}
        />
    );

    return (
        <WorkspaceLayout sidebarTitle="Mensajes" customSidebar={conversationSidebar} sidebarSections={[]}>
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))]">
                {!activeConv ? (
                    <EmptyState onNewConversation={handleNewConversation} />
                ) : (
                    <>
                        <ThreadHeader
                            conv={activeConv}
                            getOtherParticipant={getOtherParticipant}
                            wsStatus={wsStatus}
                            onBack={() => setActiveConv(null)}
                        />
                        <MessageList
                            messages={messages}
                            loading={loadingMessages}
                            currentUserId={userId}
                            onLoadOlder={loadOlderMessages}
                            onReply={setReplyTo}
                            hasMore={hasMoreOlder}
                        />
                        <MessageInput
                            token={token}
                            disabled={!activeConv}
                            sending={sending}
                            replyTo={replyTo}
                            onClearReply={() => setReplyTo(null)}
                            onSend={handleSend}
                        />
                    </>
                )}
            </div>

            <NewConversationDrawer
                isOpen={showNewConvDrawer}
                onClose={() => setShowNewConvDrawer(false)}
                query={userSearch.query}
                onQueryChange={userSearch.setQuery}
                results={userSearch.results}
                loading={userSearch.loading}
                error={userSearch.error}
                creating={creatingConv}
                onCreate={handleCreateConversation}
            />
        </WorkspaceLayout>
    );
}

export default function MessagesPageWrapper() {
    return (
        <Suspense
            fallback={
                <div className="flex h-full items-center justify-center text-sm text-[hsl(var(--text-secondary))]">
                    Cargando mensajes…
                </div>
            }
        >
            <MessagesPage />
        </Suspense>
    );
}

function ThreadHeader({
    conv,
    getOtherParticipant,
    wsStatus,
    onBack,
}: {
    conv: ConversationRead;
    getOtherParticipant: (c: ConversationRead) => { username?: string } | undefined;
    wsStatus: string;
    onBack: () => void;
}) {
    const other = getOtherParticipant(conv);
    const statusConfig =
        wsStatus === "open"
            ? { color: "fill-[hsl(var(--success))] text-[hsl(var(--success))]", label: "Activo" }
            : wsStatus === "error"
            ? { color: "fill-[hsl(var(--danger))] text-[hsl(var(--danger))]", label: "Desconectado" }
            : { color: "fill-[hsl(var(--warning))] text-[hsl(var(--warning))]", label: "Conectando..." };

    return (
        <div className="h-10 px-3 md:px-4 flex items-center gap-3 shrink-0 border-b border-[hsl(var(--border))] dark:border-white/[0.05] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))]">
            <button
                className="p-1 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] transition-all"
                aria-label="Volver a conversaciones"
                title="Volver a conversaciones"
                onClick={onBack}
            >
                <ChevronLeft size={15} />
            </button>
            <AvatarInitial name={other?.username || "U"} />
            <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">
                    {other?.username || "Usuario"}
                </p>
                <div className="flex items-center gap-1 text-2xs text-[hsl(var(--text-secondary))]">
                    <Circle size={7} className={clsx(statusConfig.color)} />
                    <span className="hidden xs:inline">{statusConfig.label}</span>
                </div>
            </div>
        </div>
    );
}

function EmptyState({ onNewConversation }: { onNewConversation: () => void }) {
    return (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center p-6">
            <div className="size-14 rounded-2xl bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                <MessageCircle size={26} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
            </div>
            <div>
                <p className="text-sm font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Selecciona una conversación</p>
                <p className="text-sm text-[hsl(var(--text-secondary))] mt-1">o empieza una nueva desde el panel izquierdo</p>
            </div>
            <button
                onClick={onNewConversation}
                aria-label="Crear nueva conversación"
                className="flex items-center gap-2 px-4 py-2 text-xs font-bold uppercase tracking-wide bg-[hsl(var(--primary))] text-white rounded-lg hover:bg-[hsl(var(--primary))] active:scale-95 transition-all shadow-sm shadow-[hsl(var(--info)/20%)] mt-1"
            >
                <Plus size={13} /> Nueva conversación
            </button>
        </div>
    );
}
