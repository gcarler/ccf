"use client";

import { AvatarInitial } from '@/components/ui/AvatarInitial';
import type { ConversationRead } from '@/types/directMessages';
import clsx from 'clsx';
import { Loader2, MessageCircle, Plus, Search, UserPlus } from 'lucide-react';

interface ConversationSidebarProps {
    conversations: ConversationRead[];
    filteredConversations: ConversationRead[];
    loading: boolean;
    error?: string | null;
    onRetry?: () => void;
    filter: string;
    onFilterChange: (value: string) => void;
    activeConvId: string | null;
    onSelectConv: (conv: ConversationRead) => void;
    onNewConv: () => void;
    totalUnread: number;
    getOtherParticipant: (conv: ConversationRead) => { username?: string } | undefined;
}

export function ConversationSidebar({
    loading,
    filteredConversations,
    error,
    onRetry,
    filter,
    onFilterChange,
    activeConvId,
    onSelectConv,
    onNewConv,
    totalUnread,
    getOtherParticipant,
}: ConversationSidebarProps) {
    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]/30 dark:bg-[hsl(var(--bg-primary))] border-r border-[hsl(var(--border))] dark:border-white/[0.05]">
            <div className="h-10 px-3 flex items-center justify-between shrink-0 border-b border-[hsl(var(--border))] dark:border-white/[0.05] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))]">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                        <MessageCircle size={12} />
                        <span className="hidden xs:inline">Mensajes</span>
                    </span>
                    {totalUnread > 0 && (
                        <span className="inline-flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-[hsl(var(--danger))] text-white text-2xs font-bold">
                            {totalUnread}
                        </span>
                    )}
                </div>
                <button
                    onClick={onNewConv}
                    className="size-6 rounded-md flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all"
                    aria-label="Nueva conversación"
                    title="Nueva conversación"
                >
                    <Plus size={13} />
                </button>
            </div>

            <div className="px-2 py-2 shrink-0">
                <div className="relative">
                    <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                    <input
                        type="text"
                        value={filter}
                        onChange={(e) => onFilterChange(e.target.value)}
                        placeholder="Buscar..."
                        aria-label="Buscar conversaciones"
                        className="w-full pl-7 pr-3 py-1.5 text-xs bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))]"
                    />
                </div>
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-thin px-1">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-10 gap-2 text-[hsl(var(--text-secondary))]">
                        <Loader2 size={16} className="animate-spin" />
                        <p className="text-xs">Cargando...</p>
                    </div>
                ) : error ? (
                    <div className="flex flex-col items-center justify-center py-10 gap-3 px-3 text-center">
                        <p className="text-xs font-semibold text-[hsl(var(--text-secondary))]">{error}</p>
                        {onRetry && (
                            <button
                                onClick={onRetry}
                                aria-label="Reintentar cargar conversaciones"
                                className="flex items-center gap-1.5 text-xs font-semibold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors"
                            >
                                <Loader2 size={12} /> Reintentar
                            </button>
                        )}
                    </div>
                ) : filteredConversations.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-10 gap-3 px-3 text-center">
                        <div className="size-10 rounded-xl bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                            <MessageCircle size={18} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
                        </div>
                        <p className="text-xs font-semibold text-[hsl(var(--text-secondary))]">
                            {filter ? 'Sin resultados' : 'Sin conversaciones'}
                        </p>
                        {!filter && (
                            <button
                                onClick={onNewConv}
                                aria-label="Iniciar nueva conversación"
                                className="flex items-center gap-1.5 text-xs font-semibold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors"
                            >
                                <UserPlus size={12} /> Iniciar chat
                            </button>
                        )}
                    </div>
                ) : (
                    filteredConversations.map((conv) => {
                        const other = getOtherParticipant(conv);
                        const isActive = activeConvId === conv.id;
                        return (
                            <button
                                key={conv.id}
                                onClick={() => onSelectConv(conv)}
                                aria-label={`Abrir conversación con ${other?.username || 'Usuario'}`}
                                className={clsx(
                                    'w-full text-left flex items-center gap-2.5 px-2 py-2 rounded-lg transition-all group mb-0.5',
                                    isActive
                                        ? 'bg-info-soft dark:bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))]'
                                        : 'hover:bg-[hsl(var(--surface-2))]/60 dark:hover:bg-white/[0.04]'
                                )}
                            >
                                <AvatarInitial name={other?.username || 'U'} size="sm" />
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-1">
                                        <p className={clsx(
                                            'text-sm font-semibold truncate',
                                            isActive ? 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]'
                                        )}>
                                            {other?.username || 'Usuario'}
                                        </p>
                                        {conv.last_message_at && (
                                            <span className="text-2xs text-[hsl(var(--text-secondary))] shrink-0">
                                                {new Date(conv.last_message_at).toLocaleTimeString(undefined, {
                                                    hour: '2-digit',
                                                    minute: '2-digit',
                                                })}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-1.5 mt-0.5">
                                        <p className="text-xs text-[hsl(var(--text-secondary))] truncate flex-1">
                                            {conv.last_message_content || 'Sin mensajes'}
                                        </p>
                                        {conv.unread_count > 0 && (
                                            <span className="inline-flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-[hsl(var(--primary))] text-white text-2xs font-bold shrink-0">
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
}
