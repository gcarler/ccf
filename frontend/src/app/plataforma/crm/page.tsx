import { Metadata } from 'next';
import { cookies } from 'next/headers';
import CRMClient from './CRMClient';
import { normalizeMembers, CrmPersona } from './types';
import { serverApiFetch } from '@/lib/serverApi';

export const metadata: Metadata = {
    title: 'Consolidación · CCF Mesh',
};

export const dynamic = 'force-dynamic';

async function fetchMembers(): Promise<CrmPersona[]> {
    const cookieStore = await cookies();
    if (!cookieStore.get('mesh_access')) {
        // SSR can render without auth state; CRMClient will hydrate and fetch
        // the directory on the client when a token is available.
        return [];
    }

    try {
        const data = await serverApiFetch<any[]>('/crm/personas/');
        return normalizeMembers(data);
    } catch {
        return [];
    }
}

export default async function CRMDashboardPage() {
    const members = await fetchMembers();
    return <CRMClient initialMembers={members} />;
}

