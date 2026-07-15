import { cookies } from 'next/headers';
import { serverApiFetch } from '@/lib/serverApi';
import type { ProjectRecord } from '@/types/projects';

export async function fetchProjects(): Promise<ProjectRecord[]> {
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
