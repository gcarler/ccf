"use client";

import React, { useState } from 'react';
import * as Popover from '@radix-ui/react-popover';
import { Command } from 'cmdk';
import { UserCircle, Search, Check, Loader2 } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import clsx from 'clsx';

interface User {
    id: string;
    username: string;
    email: string;
}

interface UserPickerProps {
    currentUserId?: string | null;
    onSelect: (userId: string) => void;
    placeholder?: string;
    className?: string;
}

export default function UserPicker({
    currentUserId,
    onSelect,
    placeholder = "Asignar a...",
    className
}: UserPickerProps) {
    const { token } = useAuth();
    const [open, setOpen] = useState(false);
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchUsers = async () => {
        if (!token || users.length > 0) return;
        setLoading(true);
        try {
            // Simplified: in a real app, we might have a specific /users/assignable endpoint
            const data = await apiFetch('/admin/personas/', { token });
            if (Array.isArray(data)) {
                setUsers(data.map((u: any) => ({
                    id: u.id,
                    username: u.nombre_completo || `${u.first_name ?? ''} ${u.last_name ?? ''}`.trim(),
                    email: u.email
                })));
            }
        } catch (err) {
            console.error("Error fetching assignable users:", err);
        } finally {
            setLoading(false);
        }
    };

    const currentUser = users.find(u => u.id === currentUserId);

    return (
        <Popover.Root open={open} onOpenChange={(val) => {
            setOpen(val);
            if (val) fetchUsers();
        }}>
            <Popover.Trigger asChild>
                <button
                    className={clsx(
                        "flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 transition-colors group text-left max-w-[150px]",
                        className
                    )}
                >
                    {currentUserId ? (
                        <div className="flex items-center gap-2 truncate">
                            <div className="size-5 rounded-full bg-slate-900 dark:bg-[hsl(var(--primary))] flex items-center justify-center font-semibold text-white shrink-0">
                                {currentUser?.username?.substring(0, 2).toUpperCase() || 'U'}
                            </div>
                            <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 truncate">
                                {currentUser?.username || `ID: ${currentUserId}`}
                            </span>
                        </div>
                    ) : (
                        <div className="flex items-center gap-2 text-slate-400 group-hover:text-slate-600">
                            <UserCircle size={16} />
                            <span className="text-[11px] font-medium">{placeholder}</span>
                        </div>
                    )}
                </button>
            </Popover.Trigger>

            <Popover.Portal>
                <Popover.Content 
                    className="z-[1000] w-64 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] rounded-md shadow-2xl border border-slate-200 dark:border-white/10 overflow-hidden animate-in fade-in zoom-in-95 duration-100"
                    sideOffset={5}
                    align="start"
                >
                    <Command className="flex flex-col">
                        <div className="flex items-center border-b border-slate-100 dark:border-white/5 px-3">
                            <Search className="mr-2 h-3.5 w-3.5 shrink-0 text-slate-400" />
                            <Command.Input 
                                placeholder="Buscar usuario..." 
                                className="flex h-9 w-full bg-transparent py-3 text-[12px] outline-none placeholder:text-slate-400"
                            />
                        </div>
                        <Command.List className="max-h-60 overflow-y-auto p-1 scrollbar-thin">
                            {loading ? (
                                <div className="flex items-center justify-center p-4">
                                    <Loader2 className="h-4 w-4 animate-spin text-[hsl(var(--primary))]" />
                                </div>
                            ) : (
                                <>
                                    <Command.Empty className="py-1.5 text-center text-[11px] text-slate-500">No se encontraron usuarios.</Command.Empty>
                                    <Command.Group>
                                        {users.map((user) => (
                                            <Command.Item
                                                key={user.id}
                                                onSelect={() => {
                                                    onSelect(user.id);
                                                    setOpen(false);
                                                }}
                                                className="flex items-center gap-3 px-3 py-2 rounded-lg text-[12px] font-bold text-slate-700 dark:text-slate-200 cursor-pointer data-[selected='true']:bg-[hsl(var(--primary))] data-[selected='true']:text-white transition-colors"
                                            >
                                                <div className="size-6 rounded-full bg-slate-100 dark:bg-white/10 flex items-center justify-center font-semibold group-data-[selected='true']:bg-white/20">
                                                    {user.username.substring(0, 2).toUpperCase()}
                                                </div>
                                                <div className="flex-1 truncate">
                                                    <p className="truncate">{user.username}</p>
                                                    <p className="text-[9px] opacity-60 truncate font-medium">{user.email}</p>
                                                </div>
                                                {currentUserId === user.id && <Check size={14} className="text-[hsl(var(--primary))] group-data-[selected='true']:text-white" />}
                                            </Command.Item>
                                        ))}
                                    </Command.Group>
                                </>
                            )}
                        </Command.List>
                    </Command>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}
