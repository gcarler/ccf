import React from 'react';
import { cookies } from 'next/headers';
import ProjectsLayoutClient from './ProjectsLayoutClient';
import { serverApiFetch } from '@/lib/serverApi';
import type { ProjectSummaryPageResponse } from '@/types/projects';

export const dynamic = 'force-dynamic';

export default async function ProjectsLayout({ children }: { children: React.ReactNode }) {
    let initialProjectPage: ProjectSummaryPageResponse | null = null;
    const cookieStore = await cookies();

    if (cookieStore.has('mesh_access')) {
        try {
            initialProjectPage = await serverApiFetch<ProjectSummaryPageResponse>('/projects/summary-page?offset=0&limit=100');
        } catch (error) {
            console.error('[ProjectsLayout] Failed to load projects for sidebar', error);
        }
    }

    return (
        <ProjectsLayoutClient initialProjectPage={initialProjectPage}>
            {children}
        </ProjectsLayoutClient>
    );
}
