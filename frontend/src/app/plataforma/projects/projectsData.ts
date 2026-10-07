import { cookies } from 'next/headers';
import { serverApiFetch } from '@/lib/serverApi';
import type { ProjectRecord, ProjectSummaryPageResponse } from '@/types/projects';

export async function fetchProjects(): Promise<ProjectRecord[]> {
    const cookieStore = await cookies();
    if (!cookieStore.has('mesh_access')) return [];

    try {
        const data = await serverApiFetch<ProjectSummaryPageResponse>('/projects/summary-page?offset=0&limit=50');
        return Array.isArray(data?.items) ? data.items : [];
    } catch (error) {
        console.error('[ProjectsPage] Failed to load projects', error);
        return [];
    }
}
