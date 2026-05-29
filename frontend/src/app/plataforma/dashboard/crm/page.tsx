import { Metadata } from 'next';
import { CrmDashboardClient } from './CrmDashboardClient';

export const metadata: Metadata = {
    title: 'Dashboard Crm · CCF Mesh',
};

export default function CrmDashboardPage() {
    return <CrmDashboardClient />;
}
