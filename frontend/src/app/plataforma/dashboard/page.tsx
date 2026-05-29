import { Metadata } from 'next';
import DashboardOverviewClient from './DashboardOverviewClient';

export const metadata: Metadata = {
    title: 'Dashboards · CCF Mesh',
};

export default function DashboardOverviewPage() {
    return <DashboardOverviewClient />;
}
