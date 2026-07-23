import type { Metadata } from 'next';

import ProjectsClient from './ProjectsClient';
import { fetchProjects } from './projectsData';

export const metadata: Metadata = {
    title: 'Proyectos · CCF Mesh',
};

export const dynamic = 'force-dynamic';

export default async function ProjectsPage() {
    const projects = await fetchProjects();
    return <ProjectsClient initialProjects={projects} initialViewType="list" />;
}
