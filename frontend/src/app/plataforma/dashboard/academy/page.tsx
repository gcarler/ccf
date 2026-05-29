import { Metadata } from 'next';
import { AcademyDashboardClient } from './AcademyDashboardClient';

export const metadata: Metadata = {
    title: 'Dashboard Academy · CCF Mesh',
};

export default function AcademyDashboardPage() {
    return <AcademyDashboardClient />;
}
