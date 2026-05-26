"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Command } from "cmdk";
import { 
    Search, 
    Users, 
    Layers, 
    GraduationCap, 
    Settings, 
    LifeBuoy, 
    Plus,
    Zap,
    Hash,
    MessageSquare,
    Globe
} from "lucide-react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import clsx from "clsx";
import { useCommandCenter, type CommandItem } from "@/context/CommandCenterContext";
import { useCreation } from "@/context/CreationContext";

export function CommandCenter() {
    const [open, setOpen] = useState(false);
    const [showShortcuts, setShowShortcuts] = useState(false);
    const router = useRouter();
    const { token } = useAuth();
    const { commands: registeredCommands } = useCommandCenter();
    const { openModal } = useCreation();

    // Toggle the menu when pressing Command+K or Ctrl+K
    useEffect(() => {
        const down = (e: KeyboardEvent) => {
            if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                setOpen((open) => !open);
            }
        };

        document.addEventListener("keydown", down);
        return () => document.removeEventListener("keydown", down);
    }, []);

    const runCommand = (command: () => void) => {
        setOpen(false);
        command();
    };

    const defaultCommands = useMemo<CommandItem[]>(() => ([
        { id: "crm", label: "CRM Pastoral", icon: Users, shortcut: "G C", group: "Acceso Rápido", action: () => router.push('/plataforma/crm') },
        { id: "projects", label: "Gestión de Proyectos", icon: Layers, shortcut: "G P", group: "Acceso Rápido", action: () => router.push('/plataforma/projects') },
        { id: "academy", label: "Academia Faro", icon: GraduationCap, shortcut: "G A", group: "Acceso Rápido", action: () => router.push('/plataforma/academy') },
        { id: "cms", label: "Panel CMS", icon: Globe, group: "Acceso Rápido", action: () => router.push('/plataforma/cms') },
        { id: "new-task", label: "Nueva Tarea...", icon: Plus, shortcut: "N T", group: "Acciones", action: () => openModal('task') },
        { id: "new-member", label: "Registrar Miembro...", icon: Plus, shortcut: "N M", group: "Acciones", action: () => router.push('/plataforma/crm/members') },
        { id: "send-message", label: "Enviar Mensaje...", icon: MessageSquare, group: "Acciones", action: () => router.push('/plataforma/crm/messaging') },
        { id: "account-settings", label: "Configuración de Cuenta", icon: Settings, group: "Soporte y Ajustes", action: () => router.push('/plataforma/account') },
        { id: "help-center", label: "Centro de Ayuda", icon: LifeBuoy, group: "Soporte y Ajustes", action: () => router.push('/plataforma/support') },
        { id: "shortcuts", label: "Atajos de Teclado", icon: Zap, group: "Soporte y Ajustes", action: () => setShowShortcuts(true) },
    ]), [openModal, router]);

    const [search, setSearch] = useState("");
    const [results, setResults] = useState<any[]>([]);
    const [isSearching, setIsSearching] = useState(false);

    // Búsqueda dinámica real
    useEffect(() => {
        const fetchResults = async () => {
            if (search.length < 2) {
                setResults([]);
                return;
            }
            setIsSearching(true);
            try {
                const data = await apiFetch<any>(`/system/search?q=${encodeURIComponent(search)}`, { token });
                setResults(data.items || []);
            } catch (err) {
                console.error(err);
            } finally {
                setIsSearching(false);
            }
        };

        const timer = setTimeout(fetchResults, 300);
        return () => clearTimeout(timer);
    }, [search, token]);

    const normalizedSearch = search.trim().toLowerCase();
    const visibleCommands = useMemo(() => {
        const allCommands = [...defaultCommands, ...registeredCommands];
        if (!normalizedSearch) return allCommands;
        return allCommands.filter((command) =>
            [command.label, command.description, command.group]
                .filter(Boolean)
                .some((value) => String(value).toLowerCase().includes(normalizedSearch))
        );
    }, [defaultCommands, normalizedSearch, registeredCommands]);

    const groupedCommands = useMemo(() => {
        const groups = new Map<string, CommandItem[]>();
        visibleCommands.forEach((command) => {
            const key = command.group || "Otros";
            const existing = groups.get(key) || [];
            existing.push(command);
            groups.set(key, existing);
        });
        return Array.from(groups.entries());
    }, [visibleCommands]);

    return (
        <AnimatePresence>
            {open && (
                <div className="fixed inset-0 z-[10000] flex items-start justify-center pt-[10vh] p-4 sm:p-3 md:p-4">
                    <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setOpen(false)}
                        className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm" 
                    />
                    
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.95, y: -20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: -20 }}
                        className="relative w-full max-w-2xl overflow-hidden rounded-lg border border-slate-200 dark:border-white/10 bg-white/80 dark:bg-[#1e1f21]/80 backdrop-blur-xl shadow-2xl shadow-black/50"
                    >
                        <Command label="Command Menu" className="flex h-full w-full flex-col" shouldFilter={false}>
                            <div className="flex items-center border-b border-slate-100 dark:border-white/5 px-3 py-1.5">
                                <Search className={clsx("mr-3 h-5 w-5 shrink-0 transition-colors", isSearching ? "text-blue-500 animate-pulse" : "text-slate-400")} />
                                <Command.Input
                                    value={search}
                                    onValueChange={setSearch}
                                    placeholder="Buscar proyectos, miembros o tareas..."
                                    className="flex h-8 w-full bg-transparent text-lg font-bold outline-none placeholder:text-slate-400 placeholder:font-medium disabled:cursor-not-allowed disabled:opacity-50"
                                />
                                <div className="ml-auto hidden items-center gap-1 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-black/20 px-2 py-1 font-semibold text-slate-400 md:flex">
                                    ESC
                                </div>
                            </div>
                            
                            <Command.List className="max-h-[450px] overflow-y-auto overflow-x-hidden p-3 scrollbar-hide">
                                {isSearching && <div className="p-4 text-center text-slate-400 text-xs font-bold uppercase tracking-wide animate-pulse">Consultando Optimus Brain...</div>}
                                
                                {!isSearching && search.length > 0 && results.length === 0 && visibleCommands.length === 0 && (
                                    <Command.Empty className="py-14 text-center">
                                        <div className="size-7 rounded-lg bg-slate-50 dark:bg-white/5 flex items-center justify-center mx-auto mb-4">
                                            <Search className="text-slate-300" />
                                        </div>
                                        <p className="text-sm font-semibold text-slate-900 dark:text-white">Sin resultados para &quot;{search}&quot;</p>
                                        <p className="text-xs text-slate-400 mt-1">Intenta con otros términos o filtros.</p>
                                    </Command.Empty>
                                )}

                                {results.length > 0 && (
                                    <Command.Group heading="Resultados de Inteligencia" className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-blue-600">
                                        {results.map((item) => (
                                            <Item 
                                                key={`${item.type}-${item.id}`} 
                                                icon={item.type === 'project' ? Layers : item.type === 'member' ? Users : Hash} 
                                                label={item.title} 
                                                description={item.detail} 
                                                onSelect={() => runCommand(() => router.push(item.href))} 
                                            />
                                        ))}
                                    </Command.Group>
                                )}

                                {groupedCommands.length > 0 && <Command.Separator className="my-4 h-[1px] bg-slate-100 dark:border-white/5" />}

                                {groupedCommands.map(([groupName, commands]) => (
                                    <Command.Group key={groupName} heading={groupName} className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                        {commands.map((cmd) => (
                                            <Item key={cmd.id} icon={cmd.icon} label={cmd.label} shortcut={cmd.shortcut} description={cmd.description} onSelect={() => runCommand(cmd.action)} />
                                        ))}
                                    </Command.Group>
                                ))}
                            </Command.List>
                        </Command>
                    </motion.div>
                </div>
            )}
            {showShortcuts && <ShortcutSheet onClose={() => setShowShortcuts(false)} />}
        </AnimatePresence>
    );
}

function Item({ icon: Icon, label, shortcut, description, onSelect }: { icon?: React.ComponentType<any>, label: string, shortcut?: string, description?: string, onSelect: () => void }) {
    return (
        <Command.Item
            onSelect={onSelect}
            className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-sm font-bold text-slate-700 dark:text-slate-200 transition-colors hover:bg-blue-500 hover:text-white data-[selected='true']:bg-blue-600 data-[selected='true']:text-white group"
        >
            {Icon ? <Icon className="h-4 w-4 shrink-0 opacity-70 group-data-[selected='true']:opacity-100" /> : <span className="h-4 w-4" />}
            <div className="flex-1">
                <span className="block leading-tight">{label}</span>
                {description && <span className="text-[11px] font-normal text-slate-400 group-data-[selected='true']:text-white/80">{description}</span>}
            </div>
            {shortcut && (
                <div className="flex items-center gap-1 rounded bg-slate-100 dark:bg-black/20 px-1.5 py-0.5 font-semibold text-slate-400 group-data-[selected='true']:bg-white/20 group-data-[selected='true']:text-white">
                    {shortcut.split(' ').map((s, i) => (
                        <span key={i}>{s}</span>
                    ))}
                </div>
            )}
        </Command.Item>
    );
}

function ShortcutSheet({ onClose }: { onClose: () => void }) {
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") onClose();
        };
        document.addEventListener("keydown", handleKeyDown);
        return () => document.removeEventListener("keydown", handleKeyDown);
    }, [onClose]);

    return (
        <div className="fixed inset-0 z-[10001] flex items-center justify-center p-4">
            <button className="absolute inset-0 bg-slate-900/45 backdrop-blur-sm" onClick={onClose} aria-label="Cerrar atajos" />
            <motion.div
                initial={{ opacity: 0, y: 12, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 12, scale: 0.98 }}
                className="relative w-full max-w-lg rounded-lg border border-slate-200 bg-white p-3 shadow-2xl dark:border-white/10 dark:bg-[#1e1f21]"
            >
                <div className="mb-5">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Atajos</p>
                    <h2 className="mt-1 text-xl font-bold text-slate-900 dark:text-white">Productividad global</h2>
                </div>
                <div className="space-y-2">
                    {[
                        ["Ctrl / Cmd + K", "Abrir centro de comandos"],
                        ["Esc", "Cerrar panel o volver un nivel"],
                        ["Modo enfoque", "Disponible desde la barra superior o el centro de comandos"],
                    ].map(([shortcut, label]) => (
                        <div key={shortcut} className="flex items-center justify-between gap-4 rounded-lg bg-slate-50 px-4 py-3 dark:bg-white/5">
                            <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">{label}</span>
                            <span className="rounded-lg border border-slate-200 bg-white px-2 py-1 font-semibold text-slate-500 dark:border-white/10 dark:bg-black/20 dark:text-slate-300">
                                {shortcut}
                            </span>
                        </div>
                    ))}
                </div>
            </motion.div>
        </div>
    );
}
