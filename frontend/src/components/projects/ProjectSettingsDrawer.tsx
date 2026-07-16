"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Save } from "lucide-react";
import { InlineTextInput } from "@/components/ui/inline-editors/InlineTextInput";
import { InlineTextArea } from "@/components/ui/inline-editors/InlineTextArea";
import { InlineProjectStatusPicker } from "@/components/ui/inline-editors/InlineProjectStatusPicker";
import { InlineUserPicker } from "@/components/ui/inline-editors/InlineUserPicker";
import type { ProjectRecord } from "@/types/projects";

interface ProjectSettingsDrawerProps {
    project: ProjectRecord | null;
    isOpen: boolean;
    onClose: () => void;
    onSave: (patch: Partial<ProjectRecord>) => void;
}

export default function ProjectSettingsDrawer({
    project,
    isOpen,
    onClose,
    onSave,
}: ProjectSettingsDrawerProps) {
    const [draft, setDraft] = useState<Partial<ProjectRecord>>({});

    useEffect(() => {
        if (isOpen && project) {
            setDraft({
                title: project.title,
                description: project.description,
                status: project.status,
                owner_id: project.owner_id,
                color: project.color,
            });
        }
    }, [isOpen, project]);

    const handleSave = () => {
        onSave(draft);
        onClose();
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-sm"
                    />
                    <motion.div
                        initial={{ x: "100%" }}
                        animate={{ x: 0 }}
                        exit={{ x: "100%" }}
                        transition={{ type: "spring", damping: 25, stiffness: 200 }}
                        className="fixed top-0 right-0 z-[101] h-full w-full max-w-md bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border-l border-[hsl(var(--border))] dark:border-white/10 shadow-2xl flex flex-col"
                    >
                        <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/5">
                            <h2 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white">
                                Editar Proyecto
                            </h2>
                            <button
                                onClick={onClose}
                                className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-colors"
                            >
                                <X size={16} />
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-5">
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    Título
                                </label>
                                <InlineTextInput
                                    value={draft.title || ""}
                                    onChange={(v) => setDraft((prev) => ({ ...prev, title: v }))}
                                    placeholder="Título del proyecto"
                                />
                            </div>

                            <div className="space-y-1">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    Descripción
                                </label>
                                <InlineTextArea
                                    value={draft.description || ""}
                                    onChange={(v) => setDraft((prev) => ({ ...prev, description: v }))}
                                    placeholder="Agregar descripción del proyecto"
                                    rows={4}
                                />
                            </div>

                            <div className="space-y-1">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    Estado
                                </label>
                                <InlineProjectStatusPicker
                                    value={draft.status || "planning"}
                                    onChange={(v) => setDraft((prev) => ({ ...prev, status: v }))}
                                />
                            </div>

                            <div className="space-y-1">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    Responsable
                                </label>
                            <div className="flex items-center gap-2">
                                <InlineUserPicker
                                    value={draft.owner_id ?? null}
                                    onChange={(id) => setDraft((prev) => ({ ...prev, owner_id: id }))}
                                />
                            </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    Color
                                </label>
                                <div className="flex items-center gap-3">
                                    <input
                                        type="color"
                                        value={draft.color || "#2563eb"}
                                        onChange={(e) => setDraft((prev) => ({ ...prev, color: e.target.value }))}
                                        className="h-10 w-20 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent cursor-pointer"
                                    />
                                    <span className="text-[12px] font-mono text-[hsl(var(--text-secondary))]">
                                        {draft.color || "#2563eb"}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="p-4 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-end gap-2">
                            <button
                                onClick={onClose}
                                className="px-4 py-2 rounded-lg text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-colors"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleSave}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[11px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all"
                            >
                                <Save size={14} /> Guardar Cambios
                            </button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
