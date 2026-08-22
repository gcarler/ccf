export interface AgendaEvent {
  id: string | number;
  title: string;
  description?: string | null;
  start_at: string;
  end_at?: string | null;
  location?: string | null;
  is_all_day: boolean;
  sede_id?: string | null;
  visibilidad?: "PUBLICO" | "SEDE" | "PRIVADO";
  created_by?: string | null;
}

export interface AgendaFormState {
  title: string;
  description: string;
  start_at: string;
  end_at: string;
  location: string;
  visibilidad?: "PUBLICO" | "SEDE" | "PRIVADO";
}

export interface PhysicalResource {
  id: string;
  nombre: string;
  tipo: string;
  capacidad?: number | null;
  ubicacion?: string | null;
  esta_activo: boolean;
  sede_id?: string | null;
}

export interface ResourceReservation {
  id: string;
  recurso_id: string;
  evento_id: string;
  fecha_inicio: string;
  fecha_fin: string;
  notas?: string | null;
}

export interface EventParticipant {
  id: string;
  evento_id: string;
  persona_id: string;
  rol?: string | null;
  estado?: string | null;
}

export interface EventComment {
  id: string;
  evento_id: string;
  author_id: string;
  contenido: string;
  created_at: string;
  updated_at?: string | null;
}
