import type { Users } from 'lucide-react';
import {
  BarChart3,
  Calendar,
  ClipboardList,
  FolderOpen,
  Sparkles,
} from 'lucide-react';

export interface Strategy {
  id: string;
  name: string;
  description: string;
  codigo?: string;
  clase_raiz?: string;
  activa: boolean;
  default_role_id?: string | null;
  typology: string;
  recurrence: string | null;
  day_of_week: string | null;
  start_time: string | null;
  event_format: string | null;
  niche_objective: string | null;
  status: 'active' | 'pending' | 'done';
  strategy_type: string;
  start_date?: string | null;
  end_date?: string | null;
  created_at: string;
  updated_at: string;
  group_count?: number;
}

export interface CustomRole {
  id: string;
  estrategia_id: string;
  nombre_rol: string;
  descripcion?: string;
}

export interface FollowUpRecord {
  id: string;
  asistencia_id: string;
  tipo: string;
  fecha_seguimiento?: string;
  observaciones?: string;
  estado_completado: boolean;
  responsable_id?: string;
}

export interface StrategyGroup {
  id: string;
  name: string;
  zone: string | null;
  leader_name: string | null;
  personas_count: number;
}

export type HabilitacionEstado = 'DESHABILITADO' | 'HABILITADO' | 'CERRADO' | 'CANCELADA';

export interface SessionRow {
  id: string;
  grupo_id: string;
  session_date: string;
  status: string;
  estado_habilitacion?: HabilitacionEstado;
  topic?: string | null;
  offering_amount?: number | null;
  report_notes?: string | null;
}

export interface AttendancePersona {
  persona_id: string;
  name: string;
  role: string;
  role_label?: string;
  status: 'present' | 'absent' | 'first_time';
  notes?: string;
}

export interface SearchablePersona {
  id: string;
  nombre_completo?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  church_role?: string;
}

export interface AttendanceSaveResult {
  evento_integracion?: {
    estado?: string;
    grupo_id?: string;
    sesion_id?: string;
    crm_consolidacion?: {
      caso_id?: string;
    } | null;
  } | null;
  metadata?: {
    trazabilidad?: string;
  } | null;
}

export type TabId = 'overview' | 'groups' | 'sessions' | 'attendance' | 'metrics';

export const STATUS_COLORS = {
  pending: '#F59E0B',
  active: '#2563EB',
  done: '#10B981',
};

export const STATUS_LABELS = {
  pending: 'No iniciada',
  active: 'Iniciada',
  done: 'Terminada',
};

export const TYPOLOGY_COLORS: Record<string, string> = {
  relacional: '#3B82F6',
  evento_masivo: '#F97316',
  sectorial: '#8B5CF6',
  reunion: '#10B981',
  cells: '#6366F1',
};

export const TYPOLOGY_LABELS: Record<string, string> = {
  relacional: 'Relacional',
  evento_masivo: 'Evento Masivo',
  sectorial: 'Sectorial',
  reunion: 'Reunión',
  cells: 'Células',
};

export const FALLBACK_MEMBER_ROLES = [
  { value: 'persona', label: 'Persona' },
  { value: 'visitante', label: 'Visitante' },
];

export const ROLE_COLORS: Record<string, string> = {
  lider: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300',
  colider: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300',
  persona: 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]',
  visitante: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  asistente: 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]',
  personalizado: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300',
};

export const TABS: { id: TabId; label: string; icon: typeof Users }[] = [
  { id: 'overview', label: 'General', icon: Sparkles },
  { id: 'groups', label: 'Grupos', icon: FolderOpen },
  { id: 'sessions', label: 'Sesiones', icon: Calendar },
  { id: 'attendance', label: 'Asistencia', icon: ClipboardList },
  { id: 'metrics', label: 'Métricas', icon: BarChart3 },
];

export const formatLocalDate = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export const normalizeRoleText = (value: string) =>
  value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

export const customRoleValue = (role: CustomRole) => `custom:${role.id}`;

export const roleMatches = (role: CustomRole, keywords: string[]) => {
  const tokens = normalizeRoleText(role.nombre_rol).split('-');
  return keywords.some(keyword => tokens.includes(keyword));
};

export const isPrimaryLeaderRole = (role: CustomRole) => {
  const tokens = normalizeRoleText(role.nombre_rol).split('-');
  return tokens.includes('lider') && !tokens.includes('co') && !tokens.includes('colider') && !tokens.includes('asistente');
};

export const isAssistantLeaderRole = (role: CustomRole) => {
  const tokens = normalizeRoleText(role.nombre_rol).split('-');
  return tokens.includes('asistente') || tokens.includes('colider') || (tokens.includes('co') && tokens.includes('lider'));
};
