"use client";

import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { AvatarInitial } from '@/components/ui/AvatarInitial';
import { Loader2, Search } from 'lucide-react';
import type { SearchedUser } from '../_hooks/useUserSearch';

interface NewConversationDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    query: string;
    onQueryChange: (value: string) => void;
    results: SearchedUser[];
    loading: boolean;
    error: string | null;
    creating: boolean;
    onCreate: (participantId: string) => void;
}

export function NewConversationDrawer({
    isOpen,
    onClose,
    query,
    onQueryChange,
    results,
    loading,
    error,
    creating,
    onCreate,
}: NewConversationDrawerProps) {
    return (
        <WorkspaceDrawer isOpen={isOpen} onClose={onClose} title="Nueva conversación" subtitle="Busca un usuario para iniciar un chat">
            <div className="space-y-4">
                <div className="relative">
                    <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => onQueryChange(e.target.value)}
                        placeholder="Buscar por nombre o email..."
                        aria-label="Buscar usuario para nueva conversación"
                        className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-sm outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:text-white"
                        autoComplete="off"
                    />
                </div>
                <div className="space-y-1">
                    {loading ? (
                        <div className="flex items-center justify-center py-8 text-[hsl(var(--text-secondary))] gap-2">
                            <Loader2 size={15} className="animate-spin" />
                            <span className="text-sm">Buscando...</span>
                        </div>
                    ) : error ? (
                        <p className="text-center py-8 text-sm text-[hsl(var(--text-secondary))]">{error}</p>
                    ) : results.length > 0 ? (
                        results.map((u) => (
                            <button
                                key={u.id}
                                onClick={() => onCreate(String(u.id))}
                                disabled={creating}
                                aria-label={`Iniciar conversación con ${u.username}`}
                                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors disabled:opacity-50 text-left"
                            >
                                <AvatarInitial name={u.username} />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">{u.username}</p>
                                    <p className="text-xs text-[hsl(var(--text-secondary))] truncate">{u.email}</p>
                                </div>
                                {creating && <Loader2 size={14} aria-hidden="true" data-testid="creating-conversation-spinner" className="animate-spin text-[hsl(var(--primary))] shrink-0" />}
                            </button>
                        ))
                    ) : (
                        <div className="flex flex-col items-center justify-center py-8 text-[hsl(var(--text-secondary))] gap-2">
                            <Search size={24} className="opacity-20" />
                            <p className="text-sm">{query.trim().length >= 2 ? 'Sin resultados' : 'Escribe para buscar'}</p>
                            {query.trim().length < 2 && <p className="text-xs">Mínimo 2 caracteres</p>}
                        </div>
                    )}
                </div>
            </div>
        </WorkspaceDrawer>
    );
}
