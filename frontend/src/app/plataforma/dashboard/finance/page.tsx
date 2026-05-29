import { Metadata } from 'next';
import { FinanceDashboardClient } from './FinanceDashboardClient';

export const metadata: Metadata = {
    title: 'Dashboard Finance · CCF Mesh',
};

export default function FinanceDashboardPage() {
    return <FinanceDashboardClient />;
}
