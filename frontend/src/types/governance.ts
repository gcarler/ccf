/**
 * Canonical TypeScript types for Governance module (CCF Platform).
 */

export interface GovernancePolicy {
  id: string;
  sede_id?: string | null;
  code: string;
  title: string;
  category: 'DOCTRINAL' | 'OPERACIONAL' | 'ADMINISTRATIVA' | 'MINISTERIAL' | string;
  content: string;
  status: 'BORRADOR' | 'EN_REVISION' | 'APROBADA' | 'PUBLICADA' | 'ARCHIVADA' | string;
  version: number;
  created_by_id?: string | null;
  approved_by_id?: string | null;
  effective_date?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GovernanceSignature {
  id: string;
  resolution_id: string;
  persona_id: string;
  persona_name?: string | null;
  signature_hash?: string | null;
  status: 'PENDIENTE' | 'FIRMADO' | 'RECHAZADO' | string;
  observations?: string | null;
  signed_at?: string | null;
  created_at: string;
}

export interface GovernanceResolution {
  id: string;
  sede_id?: string | null;
  number: string;
  title: string;
  summary?: string | null;
  content: string;
  status: 'BORRADOR' | 'APROBADA' | 'FIRMADA' | 'ARCHIVADA' | string;
  session_date?: string | null;
  created_by_id?: string | null;
  created_at: string;
  updated_at: string;
  signatures: GovernanceSignature[];
}

export interface CommitteeMember {
  id: string;
  committee_id: string;
  persona_id: string;
  persona_name?: string | null;
  role: 'PRESIDENTE' | 'SECRETARIO' | 'VOCAL' | 'ASESOR' | string;
  is_active: boolean;
  joined_at: string;
}

export interface GovernanceCommittee {
  id: string;
  sede_id?: string | null;
  name: string;
  description?: string | null;
  committee_type: 'PASTORAL' | 'FINANCIERO' | 'DISCIPLINARIO' | 'EVENTOS' | 'AUDITORIA' | string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  members: CommitteeMember[];
}

export interface GovernanceStats {
  total_policies: number;
  published_policies: number;
  total_resolutions: number;
  signed_resolutions: number;
  total_committees: number;
  active_committee_members: number;
}
