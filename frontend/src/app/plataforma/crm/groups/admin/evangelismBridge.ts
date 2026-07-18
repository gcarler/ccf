import { apiFetch } from '@/lib/http';
import type { Attendee, Season } from '@/types/crm';

type RawSeason = {
  id?: string;
  name?: string;
  status?: string | null;
};

type RawAttendee = {
  persona_id?: string;
  id?: string;
  name?: string;
  nombre_completo?: string;
};

type RawGroupDetail = {
  base_attendees?: RawAttendee[] | null;
  base_attendee_ids?: string[] | null;
  leader_id?: string | null;
  lider_id?: string | null;
  assistant_id?: string | null;
  asistente_id?: string | null;
  host_id?: string | null;
  anfitrion_id?: string | null;
};

export type CrmEvangelismGroupReportContext = {
  seasons: Season[];
  selectedSeasonId: string;
  attendees: Attendee[];
  selectedIds: string[];
  leaderId: string;
  assistantId: string;
  hostId: string;
};

function normalizeSeasonStatus(status?: string | null): string {
  const value = String(status || '').trim().toLowerCase();
  if (value === 'active' || value === 'activa') return 'Activa';
  if (value === 'closed' || value === 'finalizada') return 'Finalizada';
  if (value === 'draft' || value === 'borrador') return 'Borrador';
  return status?.trim() || 'Desconocida';
}

function normalizeSeason(raw: RawSeason): Season | null {
  if (!raw?.id || !raw?.name) return null;
  return {
    id: raw.id,
    name: raw.name,
    status: normalizeSeasonStatus(raw.status),
  };
}

function normalizeAttendee(raw: RawAttendee): Attendee | null {
  const personaId = raw.persona_id || raw.id;
  const name = raw.name || raw.nombre_completo;
  if (!personaId || !name) return null;
  return {
    persona_id: personaId,
    name,
  };
}

export async function loadCrmEvangelismGroupReportContext(token: string, groupId: string): Promise<CrmEvangelismGroupReportContext> {
  const [rawSeasons, rawDetail] = await Promise.all([
    apiFetch<RawSeason[]>('/evangelism/groups/seasons', { token }),
    apiFetch<RawGroupDetail>(`/evangelism/grupos/${groupId}`, { token }),
  ]);

  const seasons = Array.isArray(rawSeasons)
    ? rawSeasons.map(normalizeSeason).filter((season): season is Season => Boolean(season))
    : [];

  const attendees = Array.isArray(rawDetail?.base_attendees)
    ? rawDetail.base_attendees
        .map(normalizeAttendee)
        .filter((attendee): attendee is Attendee => Boolean(attendee))
    : [];

  const selectedSeasonId = (seasons.find((season) => season.status === 'Activa') || seasons[0])?.id || '';
  const fallbackIds = Array.isArray(rawDetail?.base_attendee_ids) ? rawDetail.base_attendee_ids.filter(Boolean) : [];
  const selectedIds = attendees.length > 0 ? attendees.map((attendee) => attendee.persona_id) : fallbackIds;

  return {
    seasons,
    selectedSeasonId,
    attendees,
    selectedIds,
    leaderId: rawDetail?.lider_id || rawDetail?.leader_id || '',
    assistantId: rawDetail?.asistente_id || rawDetail?.assistant_id || '',
    hostId: rawDetail?.anfitrion_id || rawDetail?.host_id || '',
  };
}

export async function createCrmEvangelismAttendanceSession(
  token: string,
  payload: { season_id: string; grupo_id: string; session_date: string },
): Promise<{ id: string }> {
  return apiFetch<{ id: string }>('/evangelism/groups/sessions', {
    method: 'POST',
    token,
    body: payload,
  });
}

export async function submitCrmEvangelismAttendance(
  token: string,
  sessionId: string,
  personaIds: string[],
): Promise<unknown> {
  return apiFetch(`/evangelism/groups/sessions/${sessionId}/attendance`, {
    method: 'POST',
    token,
    body: { persona_ids: personaIds },
  });
}
