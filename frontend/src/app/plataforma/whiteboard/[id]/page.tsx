"use client";

import React from "react";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { LayoutDashboard, Sparkles } from "lucide-react";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import { useAuth } from "@/context/AuthContext";

const WhiteboardEditor = dynamic(() => import("@/components/whiteboard/WhiteboardEditor"), { ssr: false });

export default function WhiteboardSessionPage() {
    const params = useParams();
    const projectId = (params?.id as string) ?? "";
    const { token } = useAuth();

    return (
        <div className="flex h-full flex-col overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))]">
            <WhiteboardEditor
                projectId={projectId}
                token={token}
                header={({ title, saveStatus, saveNow, isDirty }) => (
                    <WorkspaceToolbar
                        breadcrumbs={[
                            { label: "CCF Tools", icon: LayoutDashboard, href: "/plataforma/whiteboard" },
                            { label: title, icon: Sparkles },
                        ]}
                        rightActions={
                            <div className="flex items-center gap-3">
                                <div data-testid="whiteboard-save-status" className="flex items-center gap-2 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/5">
                                    {saveStatus === "saving" ? (
                                        <span>Guardando</span>
                                    ) : saveStatus === "error" ? (
                                        <span className="text-[hsl(var(--destructive))]">Error</span>
                                    ) : saveStatus === "saved" ? (
                                        <span className="text-[hsl(var(--success))]">Guardado</span>
                                    ) : isDirty ? (
                                        <span className="text-[hsl(var(--warning))]">Sin guardar</span>
                                    ) : (
                                        <span>Local</span>
                                    )}
                                </div>
                                <button
                                    onClick={saveNow}
                                    className="flex items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-white shadow-lg shadow-[hsl(var(--primary)/0.2)] transition-all hover:scale-105"
                                >
                                    Guardar
                                </button>
                            </div>
                        }
                    />
                )}
            />
        </div>
    );
}
