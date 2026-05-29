import { Metadata } from 'next';
import { AgendaDashboardClient } from './AgendaDashboardClient';

export const metadata: Metadata = {
    title: 'Dashboard Agenda · CCF Mesh',
};

export default function AgendaDashboardPage() {
    return <AgendaDashboardClient />;
}
