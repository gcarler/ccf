import { Metadata } from 'next';
import CRMClient from './CRMClient';
import { normalizeMembers, CrmMember } from './types';
import { serverApiFetch } from '@/lib/serverApi';

export const metadata: Metadata = {
    title: 'CRM Pastoral · CCF Mesh',
};

export const dynamic = 'force-dynamic';

async function fetchMembers(): Promise<CrmMember[]> {
    try {
        const data = await serverApiFetch<any[]>('/crm/members/');
        return normalizeMembers(data);
    } catch (error) {
        console.error('CRM server fetch failed', error);
        return [];
    }
}

export default async function CRMDashboardPage() {
    const members = await fetchMembers();
    return <CRMClient initialMembers={members} />;
}
