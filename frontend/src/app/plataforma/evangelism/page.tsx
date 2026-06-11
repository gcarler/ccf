import { Metadata } from 'next';
import EvangelismClient from './EvangelismClient';

export const metadata: Metadata = {
 title: 'Evangelismo y Expansión · CCF Mesh',
};

export default function EvangelismDashboardPage() {
 return <EvangelismClient />;
}

