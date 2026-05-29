import { Metadata } from 'next';
import { AdminDashboardClient } from './AdminDashboardClient';

export const metadata: Metadata = {
    title: 'Dashboard Admin · CCF Mesh',
};

export default function AdminDashboardPage() {
    return <AdminDashboardClient />;
}
