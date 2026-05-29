import { Metadata } from 'next';
import { EvangelismDashboardClient } from './EvangelismDashboardClient';

export const metadata: Metadata = {
    title: 'Dashboard Evangelism · CCF Mesh',
};

export default function EvangelismDashboardPage() {
    return <EvangelismDashboardClient />;
}
