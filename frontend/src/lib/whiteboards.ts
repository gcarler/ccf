import { apiFetch } from "./http";
import { apiUrl } from "./api";

export type GridStyle = "dots" | "lines" | "ruled" | "none";
export type GridSize = 16 | 24 | 32;

// ═════════════════════════════════════════════════════════════════════════════
// Whiteboard color constants — use these instead of hardcoded hex values
// ═════════════════════════════════════════════════════════════════════════════

export const WHITEBOARD_COLORS = {
  // Primary palette
  primary: "#2563eb",
  primaryLight: "rgba(37, 99, 235, 0.08)",
  success: "#10b981",
  successLight: "rgba(16, 185, 129, 0.1)",
  warning: "#f59e0b",
  danger: "#f43f5e",
  lavender: "#8b5cf6",
  orange: "#f97316",
  neutral: "#64748b",

  // Text colors
  textPrimary: "#0f172a",
  textSecondary: "#1e293b",

  // Background colors
  canvasLight: "#fafafa",
  canvasDark: "#ffffff",

  // Grid colors
  gridLight: "#e5e7eb",
  gridLightDot: "#cbd5e1",
  gridDark: "#1e293b",
  gridDarkDot: "#334155",
} as const;

export const WHITEBOARD_COLOR_PRESETS = [
  WHITEBOARD_COLORS.primary,
  WHITEBOARD_COLORS.success,
  WHITEBOARD_COLORS.warning,
  WHITEBOARD_COLORS.danger,
  WHITEBOARD_COLORS.lavender,
  WHITEBOARD_COLORS.orange,
  WHITEBOARD_COLORS.neutral,
  "#ffffff",
] as const;

export interface WhiteboardRecord {
  id: string;
  title: string;
  description?: string;
  created_at: string;
  updated_at?: string;
  gridStyle?: GridStyle;
  gridSize?: GridSize;
}

export interface ProjectWhiteboard {
  id: string;
  project_id: string;
  title: string;
  elements_json: string;
  created_at: string;
  updated_at?: string | null;
  thumbnail_url?: string | null;
}

export interface ProjectWhiteboardInput {
  title?: string;
  elements_json?: string;
  thumbnail_url?: string | null;
}

// ═════════════════════════════════════════════════════════════════════════════
// API remota — pizarras vinculadas a proyectos
// ═════════════════════════════════════════════════════════════════════════════

export async function fetchProjectWhiteboards(
  token: string,
  options?: { limit?: number; offset?: number }
): Promise<ProjectWhiteboard[]> {
  const data = await apiFetch<ProjectWhiteboard[]>("/projects/whiteboards", {
    token,
    query: options,
  });
  return Array.isArray(data) ? data : [];
}

export async function fetchProjectWhiteboard(
  projectId: string,
  token: string
): Promise<ProjectWhiteboard | null> {
  const data = await apiFetch<ProjectWhiteboard | null>(
    `/projects/${projectId}/whiteboard`,
    { token }
  );
  return data ?? null;
}

export async function saveProjectWhiteboard(
  projectId: string,
  input: ProjectWhiteboardInput,
  token: string
): Promise<ProjectWhiteboard> {
  return apiFetch<ProjectWhiteboard>(`/projects/${projectId}/whiteboard`, {
    method: "POST",
    token,
    body: input,
  });
}

export async function deleteProjectWhiteboard(
  projectId: string,
  token: string
): Promise<void> {
  await apiFetch(`/projects/${projectId}/whiteboard`, {
    method: "DELETE",
    token,
  });
}

export interface WhiteboardThumbnailResult {
  thumbnail_url: string;
}

/** Uploads a thumbnail image for the board. Returns the persisted storage URL. */
export async function uploadProjectWhiteboardThumbnail(
  projectId: string,
  blob: Blob,
  token: string
): Promise<string> {
  const form = new FormData();
  form.append("file", blob, "thumbnail.png");
  const data = await apiFetch<WhiteboardThumbnailResult>(
    `/projects/${projectId}/whiteboard/thumbnail`,
    { method: "POST", token, body: form }
  );
  return data?.thumbnail_url ?? "";
}

/** Converts a canvas data URL into a Blob (best-effort; null on failure). */
export function dataUrlToBlob(dataUrl: string): Blob | null {
  try {
    const [head, base64] = dataUrl.split(",");
    const mime = /data:(.*?);base64/.exec(head)?.[1] || "image/png";
    const bin = atob(base64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
    return new Blob([bytes], { type: mime });
  } catch {
    return null;
  }
}

/** Resolves an API-relative static URL (e.g. "/api/static/...") to an absolute one. */
export function resolveApiUrl(path: string): string {
  if (!path) return path;
  if (/^https?:\/\//.test(path)) return path;
  return apiUrl(path);
}
