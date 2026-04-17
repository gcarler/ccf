import type { Metadata } from 'next';
import ProjectsClient from './ProjectsClient';
import { serverApiFetch } from '@/lib/serverApi';
import type { ProjectRecord } from '@/types/projects';

export const metadata: Metadata = {
    title: 'Proyectos · CCF Mesh',
};

export const dynamic = 'force-dynamic';

async function fetchProjects(): Promise<ProjectRecord[]> {
    try {
        const data = await serverApiFetch<ProjectRecord[]>('/projects');
        return Array.isArray(data) ? data : [];
    } catch (error) {
        console.error('projects fetch failed', error);
        return [];
    }
}

export default async function ProjectsPage() {
    const projects = await fetchProjects();
    return <ProjectsClient initialProjects={projects} />;
}

