"use client";

import React from "react";
import { createPortal } from "react-dom";
import {
    Cloud,
    Loader2,
    X,
    PencilRuler,
    Sparkles,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import WhiteboardEditor from "@/components/whiteboard/WhiteboardEditor";

interface Props {
    project_id: string;
    isOpen: boolean;
    onClose: () => void;
}

export default function ProjectWhiteboard({
    project_id,
    isOpen,
    onClose,
}: Props) {
    const { token } = useAuth();

    // Mount/unmount the editor whenever the modal opens/closes. This guarantees
    // the Fabric.js canvas is initialized on a visible, attached DOM element and
    // avoids stale state from previous sessions.
    if (!isOpen) return null;

    const whiteboard = (
        <div
            className="fixed inset-0 z-[9999] flex flex-col bg-[hsl(var(--bg-secondary))] dark:bg-[hsl(var(--bg-primary))]"
            role="application"
            aria-label="Pizarra del proyecto"
        >
            <WhiteboardEditor
                projectId={project_id}
                token={token}
                header={({ title, saveStatus, saveNow }) => (
                    <header className="h-11 px-4 shrink-0 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] shadow-sm">
                        <div className="flex items-center gap-3">
                            <div className="size-7 rounded-md bg-orange-500 flex items-center justify-center text-white">
                                <PencilRuler size={14} />
                            </div>
                            <span className="text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wide">
                                {title || "Pizarra del Proyecto"}
                            </span>
                            <div className="flex items-center gap-1.5 ml-2">
                                {saveStatus === "saving" ? (
                                    <>
                                        <Loader2 size={10} className="animate-spin text-[hsl(var(--primary))]" />
                                        <span className="text-[9px] font-semibold uppercase text-[hsl(var(--primary))]">Guardando...</span>
                                    </>
                                ) : saveStatus === "error" ? (
                                    <>
                                        <Cloud size={10} className="text-[hsl(var(--danger))]" />
                                        <span className="text-[9px] font-semibold uppercase text-[hsl(var(--danger))]">Error</span>
                                    </>
                                ) : saveStatus === "saved" ? (
                                    <>
                                        <Cloud size={10} className="text-[hsl(var(--success))]" />
                                        <span className="text-[9px] font-semibold uppercase text-[hsl(var(--success))]">Guardado</span>
                                    </>
                                ) : (
                                    <>
                                        <Cloud size={10} className="text-[hsl(var(--success))]" />
                                        <span className="text-[9px] font-semibold uppercase text-[hsl(var(--success))]">Listo</span>
                                    </>
                                )}
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={saveNow}
                                className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-bold uppercase tracking-wide hover:opacity-90 transition-opacity shadow-md"
                            >
                                <Sparkles size={11} /> Guardar
                            </button>
                            <button
                                onClick={onClose}
                                className="p-1.5 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 transition-all"
                                title="Cerrar (Esc)"
                            >
                                <X size={16} />
                            </button>
                        </div>
                    </header>
                )}
            />
        </div>
    );

    return createPortal(whiteboard, document.body);
}
