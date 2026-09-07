export interface AgendaEvent {
  id: number;
  title: string;
  description?: string | null;
  start_at: string;
  end_at?: string | null;
  location?: string | null;
  is_all_day: boolean;
  recurrence_rule?: string | null;
  recurrence_until?: string | null;
  recurrence_exceptions?: string[];
  recurrence_id?: string | null;
  is_recurring?: boolean;
}

export type AgendaRecurrencePreset = "" | "DAILY" | "WEEKLY" | "BIWEEKLY" | "MONTHLY";

export interface AgendaFormState {
  title: string;
  description: string;
  start_at: string;
  end_at: string;
  location: string;
  recurrence: AgendaRecurrencePreset;
  recurrence_until: string;
}

const PRESET_BY_RULE: Record<string, AgendaRecurrencePreset> = {
  "RRULE:FREQ=DAILY": "DAILY",
  "RRULE:FREQ=WEEKLY": "WEEKLY",
  "RRULE:FREQ=WEEKLY;INTERVAL=2": "BIWEEKLY",
  "RRULE:FREQ=MONTHLY": "MONTHLY",
};

/** Mapea una RRULE conocida de vuelta al preset del formulario ("" si no coincide). */
export function presetFromRule(rule?: string | null): AgendaRecurrencePreset {
  if (!rule) return "";
  return PRESET_BY_RULE[rule.trim().toUpperCase()] ?? "";
}

/** Construye la RRULE RFC 5545 a partir del preset del formulario. */
export function buildRecurrenceRule(preset: AgendaRecurrencePreset): string | null {
  switch (preset) {
    case "DAILY":
      return "RRULE:FREQ=DAILY";
    case "WEEKLY":
      return "RRULE:FREQ=WEEKLY";
    case "BIWEEKLY":
      return "RRULE:FREQ=WEEKLY;INTERVAL=2";
    case "MONTHLY":
      return "RRULE:FREQ=MONTHLY";
    default:
      return null;
  }
}

const RECURRENCE_LABELS: Record<string, string> = {
  "RRULE:FREQ=DAILY": "Se repite todos los días",
  "RRULE:FREQ=WEEKLY": "Se repite semanalmente",
  "RRULE:FREQ=WEEKLY;INTERVAL=2": "Se repite cada 2 semanas",
  "RRULE:FREQ=MONTHLY": "Se repite mensualmente",
};

/** Etiqueta legible de una regla de recurrencia conocida. */
export function describeRecurrence(rule?: string | null): string | null {
  if (!rule) return null;
  return RECURRENCE_LABELS[rule.trim().toUpperCase()] ?? "Evento recurrente";
}
