import type { CmsSection } from '@/types/cms-v2';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';
import type { SectionSnapshot } from '@/lib/cms/versionDiff';

// ── Projects ────────────────────────────────────────────────────────────────

export function createMockProject(overrides: Partial<ProjectRecord> = {}): ProjectRecord {
  return {
    id: 'p1',
    title: 'Proyecto de prueba',
    status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockTask(overrides: Partial<ProjectTaskRecord> = {}): ProjectTaskRecord {
  return {
    id: 't1',
    project_id: 'p1',
    title: 'Tarea de prueba',
    status: 'todo',
    priority: 'medium',
    ...overrides,
  };
}

// ── CRM / Evangelism persona ────────────────────────────────────────────────

export interface CrmPersonaRow {
  id: string;
  nombre_completo: string;
  email: string;
  phone: string;
  church_role: string;
  spiritual_status: string;
}

export function createMockCrmPersona(overrides: Partial<CrmPersonaRow> = {}): CrmPersonaRow {
  return {
    id: '1',
    nombre_completo: 'Ana Martínez',
    email: 'ana@example.com',
    phone: '3001234567',
    church_role: 'líder',
    spiritual_status: 'creyente',
    ...overrides,
  };
}

// Shape expected by the PersonaSelect component (first_name/last_name OR nombre_completo).
export interface PersonaSelectOption {
  id: string;
  first_name?: string;
  last_name?: string;
  nombre_completo?: string;
  church_role?: string;
  spiritual_status?: string;
}

export function createMockPersonaSelectOption(
  overrides: Partial<PersonaSelectOption> = {},
): PersonaSelectOption {
  return {
    id: '1',
    first_name: 'Juan',
    last_name: 'Pérez',
    church_role: 'Persona',
    ...overrides,
  };
}

// ── CMS ─────────────────────────────────────────────────────────────────────

export function createMockCmsSection<T extends string = string>(
  type: T,
  overrides: Partial<CmsSection<T>> = {},
): CmsSection<T> {
  const base: CmsSection<T> = {
    id: 'section-1',
    page_id: 'page-1',
    section_key: `key-${type}`,
    type,
    props_json: {} as CmsSection<T>['props_json'],
    sort_order: 0,
    is_visible: true,
    status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
  return { ...base, ...overrides };
}

export function createMockSectionSnapshot(overrides: Partial<SectionSnapshot> = {}): SectionSnapshot {
  return {
    ...overrides,
  };
}
