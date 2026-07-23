import { permanentRedirect } from 'next/navigation';

export const dynamic = 'force-dynamic';

export default function ProjectsListPage() {
    permanentRedirect('/plataforma/projects?view=list#projects-list');
}
