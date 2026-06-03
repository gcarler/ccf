import { Metadata } from 'next';
import CRMClient from './CRMClient';

export const metadata: Metadata = {
    title: 'Consolidación · CCF Mesh',
};

export const dynamic = 'force-dynamic';

export default function CRMDashboardPage() {
    return <CRMClient />;
}
