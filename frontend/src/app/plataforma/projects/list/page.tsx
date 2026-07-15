import type { Metadata } from 'next';
import ProjectsClient from '../ProjectsClient';
import { fetchProjects } from '../projectsData';

export const metadata: Metadata = {
    title: 'Proyectos · Lista · CCF Mesh',
};

export const dynamic = 'force-dynamic';

export default async function ProjectsListPage() {
    const projects = await fetchProjects();
    return <ProjectsClient initialProjects={projects} initialViewType="list" />;
}
