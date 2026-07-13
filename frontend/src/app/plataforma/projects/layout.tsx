import React from 'react';
import { cookies } from 'next/headers';
import ProjectsLayoutClient from './ProjectsLayoutClient';
import { serverApiFetch } from '@/lib/serverApi';
import type { ProjectRecord } from '@/types/projects';

export const dynamic = 'force-dynamic';

export default async function ProjectsLayout({ children }: { children: React.ReactNode }) {
    let initialProjects: ProjectRecord[] = [];
    const cookieStore = await cookies();
    
    if (cookieStore.has('mesh_access')) {
        try {
            const data = await serverApiFetch<ProjectRecord[]>('/projects');
            initialProjects = Array.isArray(data) ? data : [];
        } catch (error) {
            console.error('[ProjectsLayout] Failed to load projects for sidebar', error);
        }
    }

    return (
        <ProjectsLayoutClient initialProjects={initialProjects}>
            {children}
        </ProjectsLayoutClient>
    );
}
