import type { Metadata } from 'next';
import { cookies } from 'next/headers';
import ProjectsClient from './ProjectsClient';
import { serverApiFetch } from '@/lib/serverApi';
import type { ProjectRecord } from '@/types/projects';

export const metadata: Metadata = {
    title: 'Proyectos · CCF Mesh',
};

export const dynamic = 'force-dynamic';

async function fetchProjects(): Promise<ProjectRecord[]> {
    const cookieStore = await cookies();
    if (!cookieStore.has('mesh_access')) return [];

    try {
        const data = await serverApiFetch<ProjectRecord[]>('/projects');
        return Array.isArray(data) ? data : [];
    } catch (error) {
        console.error('[ProjectsPage] Failed to load projects', error);
        return [];
    }
}

export default async function ProjectsPage() {
    const projects = await fetchProjects();
    return <ProjectsClient initialProjects={projects} />;
}
