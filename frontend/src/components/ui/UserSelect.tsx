"use client";

import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Check, ChevronDown, User as UserIcon, Search } from "lucide-react";

interface UserOption {
    id: number;
    username: string;
    email: string;
    role?: string;
}

interface UserSelectProps {
    value: number | null;
    onChange: (userId: number | null) => void;
    placeholder?: string;
    className?: string;
}

export default function UserSelect({
    value,
    onChange,
    placeholder = "Sin asignar",
    className = "",
}: UserSelectProps) {
    const { token } = useAuth();
    const [open, setOpen] = useState(false);
    const [users, setUsers] = useState<UserOption[]>([]);
    const [search, setSearch] = useState("");
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!token || users.length > 0) return;
        apiFetch<UserOption[]>("/auth/user-list", { token })
            .then(setUsers)
            .catch(() => {});
    }, [token, users.length]);

    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const selected = users.find((u) => u.id === value);

    const filtered = search.trim()
        ? users.filter(
              (u) =>
                  u.username.toLowerCase().includes(search.toLowerCase()) ||
                  u.email.toLowerCase().includes(search.toLowerCase())
          )
        : users;

    return (
        <div ref={ref} className={`relative ${className}`}>
            <button
                type="button"
                onClick={() => setOpen(!open)}
                className="w-full flex items-center gap-2 rounded-md border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 px-3 py-2 text-sm font-medium text-left hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
            >
                {selected ? (
                    <>
                        <div className="size-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                            <UserIcon size={12} className="text-blue-600 dark:text-blue-400" />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                                {selected.username}
                            </p>
                            <p className="text-[10px] text-slate-400 truncate">{selected.email}</p>
                        </div>
                    </>
                ) : (
                    <span className="text-xs text-slate-400">{placeholder}</span>
                )}
                <ChevronDown
                    size={14}
                    className={`ml-auto shrink-0 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
                />
            </button>

            {open && (
                <div className="absolute z-50 mt-1 w-full rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-[#1E1F21] shadow-xl max-h-72 overflow-hidden">
                    <div className="p-2 border-b border-slate-100 dark:border-white/5">
                        <div className="flex items-center gap-2 rounded-md bg-slate-100 dark:bg-white/5 px-2 py-1.5">
                            <Search size={12} className="text-slate-400 shrink-0" />
                            <input
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Buscar usuario..."
                                className="bg-transparent text-xs font-medium outline-none w-full text-slate-900 dark:text-white placeholder:text-slate-400"
                            />
                        </div>
                    </div>
                    <div className="overflow-y-auto max-h-56">
                        <button
                            type="button"
                            onClick={() => {
                                onChange(null);
                                setOpen(false);
                                setSearch("");
                            }}
                            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-left"
                        >
                            <div className="size-6 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                                <UserIcon size={12} className="text-slate-400" />
                            </div>
                            Sin asignar
                            {value === null && <Check size={12} className="ml-auto text-blue-500" />}
                        </button>
                        {filtered.map((user) => (
                            <button
                                key={user.id}
                                type="button"
                                onClick={() => {
                                    onChange(user.id);
                                    setOpen(false);
                                    setSearch("");
                                }}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-left"
                            >
                                <div className="size-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                                    <UserIcon size={12} className="text-blue-600 dark:text-blue-400" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                                        {user.username}
                                    </p>
                                    <p className="text-[10px] text-slate-400 truncate">{user.email}</p>
                                </div>
                                {user.id === value && (
                                    <Check size={12} className="ml-auto shrink-0 text-blue-500" />
                                )}
                            </button>
                        ))}
                        {filtered.length === 0 && (
                            <p className="px-3 py-4 text-center text-[10px] text-slate-400">
                                No se encontraron usuarios
                            </p>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
