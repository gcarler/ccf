import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
    title: 'Proyectos · CCF Mesh',
};

export const dynamic = 'force-dynamic';

export default async function ProjectsPage() {
    redirect('/plataforma/projects/list#projects-list');
}
