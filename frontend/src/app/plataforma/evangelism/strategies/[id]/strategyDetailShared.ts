import {
  BarChart3,
  Calendar,
  ClipboardList,
  FolderOpen,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';

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
  pending: 'hsl(var(--warning))',
  active: 'hsl(var(--primary))',
  done: 'hsl(var(--success))',
};

export const STATUS_LABELS = {
  pending: 'No iniciada',
  active: 'Iniciada',
  done: 'Terminada',
};

export const TYPOLOGY_COLORS: Record<string, string> = {
  relacional: 'hsl(var(--info))',
  evento_masivo: 'hsl(var(--warning))',
  sectorial: 'hsl(var(--primary))',
  reunion: 'hsl(var(--success))',
  cells: 'hsl(var(--primary))',
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
  lider: 'bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/30 dark:text-info-text',
  colider: 'bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/30 dark:text-info-text',
  persona: 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]',
  visitante: 'bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))] dark:bg-[hsl(var(--warning)/0.15)] dark:text-[hsl(var(--warning))]',
  asistente: 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]',
  personalizado: 'bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/30 dark:text-info-text',
};

export const TABS: { id: TabId; label: string; icon: LucideIcon }[] = [
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
