import { Metadata } from 'next';
import { CmsDashboardClient } from './CmsDashboardClient';

export const metadata: Metadata = {
    title: 'Dashboard Cms · CCF Mesh',
};

export default function CmsDashboardPage() {
    return <CmsDashboardClient />;
}
