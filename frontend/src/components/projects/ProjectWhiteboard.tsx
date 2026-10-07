"use client";

import React from "react";
import dynamic from "next/dynamic";
import { createPortal } from "react-dom";
import { useAuth } from "@/context/AuthContext";
import ProjectWhiteboardHeader from "@/components/projects/ProjectWhiteboardHeader";

const WhiteboardEditor = dynamic(() => import("@/components/whiteboard/WhiteboardEditor"), { ssr: false });

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

    // Mount/unmount the editor whenever the board opens/closes. This guarantees
    // the Fabric.js canvas is initialized on a visible, attached DOM element and
    // avoids stale state from previous sessions.
    if (!isOpen) return null;

    const whiteboard = (
        <div
            className="fixed inset-0 z-[9999] flex flex-col bg-[hsl(var(--surface-1))]"
            role="application"
            aria-label="Pizarra del proyecto"
        >
            <WhiteboardEditor
                projectId={project_id}
                token={token}
                header={({ title, saveStatus, saveNow, isDirty, hasConflict }) => (
                    <ProjectWhiteboardHeader
                        title={title}
                        saveStatus={saveStatus}
                        saveNow={saveNow}
                        isDirty={isDirty}
                        hasConflict={hasConflict}
                        onClose={onClose}
                    />
                )}
            />
        </div>
    );

    return createPortal(whiteboard, document.body);
}
