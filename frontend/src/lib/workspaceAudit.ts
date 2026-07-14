export interface WorkspaceAuditEvent {
  timestamp: string;
  action: string;
  feature_id?: string | null;
  updated_by?: string | null;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  changes?: Record<string, unknown> | null;
  [key: string]: unknown;
}

function stringifyPart(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function getWorkspaceAuditEventKey(event: WorkspaceAuditEvent): string {
  return [
    event.timestamp,
    event.action,
    event.feature_id ?? "",
    event.updated_by ?? "",
    stringifyPart(event.changes ?? null),
    stringifyPart(event.before ?? null),
    stringifyPart(event.after ?? null),
  ].join("|");
}
