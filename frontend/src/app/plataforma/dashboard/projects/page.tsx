import { Metadata } from 'next';
import { ProjectsDashboardClient } from './ProjectsDashboardClient';

export const metadata: Metadata = {
    title: 'Dashboard Projects · CCF Mesh',
};

export default function ProjectsDashboardPage() {
    return <ProjectsDashboardClient />;
}
