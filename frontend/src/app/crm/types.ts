export interface CrmMember {
    id: number;
    name: string;
    email?: string | null;
    group?: string | null;
    status: string;
    phone?: string | null;
    joinedAt?: string | null;
    church_role?: string | null;
    family_id?: number | null;
}

export interface CrmAnalyticsSummary {
    total_members: number;
    active_members: number;
    total_leads: number;
    pipeline_by_stage: Record<string, number>;
    open_counseling: number;
    events_this_month: number;
    total_groups: number;
    total_families: number;
}

export function normalizeMembers(payload: any[]): CrmMember[] {
    if (!Array.isArray(payload)) return [];
    return payload.map((m) => ({
        id: m.id,
        name: `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim(),
        email: m.email,
        group: m.group || (m.glory_house_id ? `Casa #${m.glory_house_id}` : 'Sin Grupo'),
        status: m.spiritual_status || m.status || 'Nuevo',
        phone: m.phone,
        joinedAt: m.created_at,
        church_role: m.church_role || 'Miembro',
        family_id: m.family_id,
    }));
}
