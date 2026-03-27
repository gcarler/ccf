export interface CrmMember {
    id: number;
    name: string;
    email?: string | null;
    group?: string | null;
    status: string;
    phone?: string | null;
    joinedAt?: string | null;
    church_role?: string | null;
}

export function normalizeMembers(payload: any[]): CrmMember[] {
    if (!Array.isArray(payload)) return [];
    return payload.map((m) => ({
        id: m.id,
        name: `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim(),
        email: m.email,
        group: m.glory_house_id ? `Casa #${m.glory_house_id}` : 'Sin Grupo',
        status: m.status || 'Nuevo',
        phone: m.phone,
        joinedAt: m.created_at,
        church_role: m.church_role || 'Miembro',
    }));
}
