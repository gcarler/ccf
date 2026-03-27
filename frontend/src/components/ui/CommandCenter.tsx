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
    Calendar,
    Zap,
    Hash,
    MessageSquare,
    Globe
} from "lucide-react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useCommandCenter } from "@/context/CommandCenterContext";
import type { CommandItem } from "@/context/CommandCenterContext";

export function CommandCenter() {
    const [open, setOpen] = useState(false);
    const router = useRouter();
    const { commands: contextualCommands } = useCommandCenter();

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
        { id: "crm", label: "CRM Pastoral", icon: Users, shortcut: "G C", group: "Acceso Rápido", action: () => router.push('/crm') },
        { id: "projects", label: "Gestión de Proyectos", icon: Layers, shortcut: "G P", group: "Acceso Rápido", action: () => router.push('/projects') },
        { id: "academy", label: "Academia Faro", icon: GraduationCap, shortcut: "G A", group: "Acceso Rápido", action: () => router.push('/academy') },
        { id: "cms", label: "Panel CMS", icon: Globe, group: "Acceso Rápido", action: () => router.push('/cms') },
        { id: "new-task", label: "Nueva Tarea...", icon: Plus, shortcut: "N T", group: "Acciones", action: () => router.push('/projects') },
        { id: "new-member", label: "Registrar Miembro...", icon: Plus, shortcut: "N M", group: "Acciones", action: () => router.push('/crm/members') },
        { id: "send-message", label: "Enviar Mensaje...", icon: MessageSquare, group: "Acciones", action: () => router.push('/crm/messaging') },
        { id: "account-settings", label: "Configuración de Cuenta", icon: Settings, group: "Soporte y Ajustes", action: () => router.push('/account') },
        { id: "help-center", label: "Centro de Ayuda", icon: LifeBuoy, group: "Soporte y Ajustes", action: () => router.push('/support') },
        { id: "shortcuts", label: "Atajos de Teclado", icon: Zap, group: "Soporte y Ajustes", action: () => {} },
    ]), [router]);

    const contextualGroups = useMemo(() => {
        if (!contextualCommands.length) return [] as Array<[string, CommandItem[]]>;
        const grouped = new Map<string, CommandItem[]>();
        contextualCommands.forEach((cmd) => {
            const key = cmd.group || "Contextual";
            grouped.set(key, [...(grouped.get(key) || []), cmd]);
        });
        return Array.from(grouped.entries());
    }, [contextualCommands]);

    return (
        <AnimatePresence>
            {open && (
                <div className="fixed inset-0 z-[10000] flex items-start justify-center pt-[10vh] p-4 sm:p-6 md:p-20">
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
                        className="relative w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#1e1f21] shadow-2xl shadow-black/50"
                    >
                        <Command label="Command Menu" className="flex h-full w-full flex-col">
                            <div className="flex items-center border-b border-slate-100 dark:border-white/5 px-4">
                                <Search className="mr-3 h-4 w-4 shrink-0 text-slate-400" />
                                <Command.Input
                                    placeholder="Escribe un comando o busca algo..."
                                    className="flex h-12 w-full bg-transparent py-3 text-sm font-medium outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
                                />
                                <div className="ml-auto hidden items-center gap-1 rounded border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-1.5 py-0.5 text-[10px] font-black text-slate-400 md:flex">
                                    ESC
                                </div>
                            </div>
                            
                            <Command.List className="max-h-[400px] overflow-y-auto overflow-x-hidden p-2 scrollbar-thin">
                                <Command.Empty className="py-10 text-center text-sm text-slate-500">No se encontraron resultados.</Command.Empty>
                                
                                {['Acceso Rápido', 'Acciones', 'Soporte y Ajustes'].map((groupName, idx) => (
                                    <React.Fragment key={groupName}>
                                        <Command.Group heading={groupName} className="px-2 py-1.5 text-[10px] font-black uppercase tracking-widest text-slate-400">
                                            {defaultCommands
                                                .filter((cmd) => cmd.group === groupName)
                                                .map((cmd) => (
                                                    <Item key={cmd.id} icon={cmd.icon} label={cmd.label} shortcut={cmd.shortcut} description={cmd.description} onSelect={() => runCommand(cmd.action)} />
                                                ))}
                                        </Command.Group>
                                        {idx < 2 && <Command.Separator className="my-2 h-[1px] bg-slate-100 dark:bg-white/5" />}
                                    </React.Fragment>
                                ))}

                                {contextualGroups.length > 0 && <Command.Separator className="my-2 h-[1px] bg-slate-100 dark:bg-white/5" />}

                                {contextualGroups.map(([groupName, items], idx) => (
                                    <React.Fragment key={groupName}>
                                        <Command.Group heading={groupName} className="px-2 py-1.5 text-[10px] font-black uppercase tracking-widest text-slate-400">
                                            {items.map((cmd) => (
                                                <Item key={cmd.id} icon={cmd.icon} label={cmd.label} shortcut={cmd.shortcut} description={cmd.description} onSelect={() => runCommand(cmd.action)} />
                                            ))}
                                        </Command.Group>
                                        {idx < contextualGroups.length - 1 && <Command.Separator className="my-2 h-[1px] bg-slate-100 dark:bg-white/5" />}
                                    </React.Fragment>
                                ))}
                            </Command.List>
                        </Command>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}

function Item({ icon: Icon, label, shortcut, description, onSelect }: { icon?: React.ComponentType<any>, label: string, shortcut?: string, description?: string, onSelect: () => void }) {
    return (
        <Command.Item
            onSelect={onSelect}
            className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold text-slate-700 dark:text-slate-200 transition-colors hover:bg-blue-500 hover:text-white data-[selected='true']:bg-blue-600 data-[selected='true']:text-white group"
        >
            {Icon ? <Icon className="h-4 w-4 shrink-0 opacity-70 group-data-[selected='true']:opacity-100" /> : <span className="h-4 w-4" />}
            <div className="flex-1">
                <span className="block leading-tight">{label}</span>
                {description && <span className="text-[11px] font-normal text-slate-400 group-data-[selected='true']:text-white/80">{description}</span>}
            </div>
            {shortcut && (
                <div className="flex items-center gap-1 rounded bg-slate-100 dark:bg-black/20 px-1.5 py-0.5 text-[10px] font-black text-slate-400 group-data-[selected='true']:bg-white/20 group-data-[selected='true']:text-white">
                    {shortcut.split(' ').map((s, i) => (
                        <span key={i}>{s}</span>
                    ))}
                </div>
            )}
        </Command.Item>
    );
}
