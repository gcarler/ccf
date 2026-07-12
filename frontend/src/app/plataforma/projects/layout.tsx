import React from 'react';
import ProjectsLayoutClient from './ProjectsLayoutClient';
import { serverApiFetch } from '@/lib/serverApi';
import type { ProjectRecord } from '@/types/projects';
import { toast } from "sonner";

export const dynamic = 'force-dynamic';

export default async function ProjectsLayout({ children }: { children: React.ReactNode }) {
    let initialProjects: ProjectRecord[] = [];
    
    try {
        const data = await serverApiFetch<ProjectRecord[]>('/projects');
        initialProjects = Array.isArray(data) ? data : [];
    } catch (error) {
        toast.error("Error pre-fetching projects for layout");
    }

    return (
        <ProjectsLayoutClient initialProjects={initialProjects}>
            {children}
        </ProjectsLayoutClient>
    );
}
