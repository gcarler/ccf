"use client";

import React from 'react';
import RightPanel from '@/components/ui/RightPanel';
import { ProjectWBSTreeView } from './ProjectWBSTreeView';
import type { WBSNode } from '@/types/projects';
import { ListTree } from 'lucide-react';

interface ProjectWBSDrawerProps {
    projectId: string;
    projectTitle?: string;
    isOpen: boolean;
    onClose: () => void;
    onSelectNode?: (node: WBSNode) => void;
}

export function ProjectWBSDrawer({
    projectId,
    projectTitle = 'Proyecto',
    isOpen,
    onClose,
    onSelectNode,
}: ProjectWBSDrawerProps) {
    return (
        <RightPanel
            isOpen={isOpen}
            onClose={onClose}
            title={
                <div className="flex items-center gap-2">
                    <ListTree className="text-[hsl(var(--primary))]" size={18} />
                    <span className="font-bold text-sm uppercase tracking-tight">
                        Estructura de Desglose del Trabajo (EDT / WBS)
                    </span>
                </div>
            }
            subtitle={
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    Organigrama Jerárquico y Codificación Recursiva • {projectTitle}
                </span>
            }
            width="w-full sm:max-w-2xl md:max-w-3xl"
        >
            <div className="p-4 sm:p-6">
                <ProjectWBSTreeView
                    projectId={projectId}
                    projectTitle={projectTitle}
                    onSelectNode={onSelectNode}
                />
            </div>
        </RightPanel>
    );
}
