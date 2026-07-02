import { apiFetch } from "./http";

export type GridStyle = "dots" | "lines" | "ruled" | "none";
export type GridSize = 16 | 24 | 32;

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

export const WHITEBOARDS_KEY = "ccf_whiteboards";

export function whiteboardCanvasKey(id: string) {
  return `ccf_whiteboard:${id}:canvas`;
}

export function normalizeWhiteboardRecord(value: unknown): WhiteboardRecord | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Partial<WhiteboardRecord>;
  if (!item.id || !item.title || !item.created_at) return null;
  return {
    id: String(item.id),
    title: String(item.title),
    description: item.description ? String(item.description) : "",
    created_at: String(item.created_at),
    updated_at: item.updated_at ? String(item.updated_at) : undefined,
    gridStyle: item.gridStyle && ["dots", "lines", "ruled", "none"].includes(item.gridStyle as string)
      ? (item.gridStyle as GridStyle) : undefined,
    gridSize: item.gridSize && [16, 24, 32].includes(Number(item.gridSize))
      ? Number(item.gridSize) as GridSize : undefined,
  };
}

export function readWhiteboards(storage: Storage): WhiteboardRecord[] {
  try {
    const parsed = JSON.parse(storage.getItem(WHITEBOARDS_KEY) || "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map(normalizeWhiteboardRecord)
      .filter((item): item is WhiteboardRecord => Boolean(item));
  } catch {
    return [];
  }
}

export function writeWhiteboards(storage: Storage, boards: WhiteboardRecord[]) {
  storage.setItem(WHITEBOARDS_KEY, JSON.stringify(boards));
}

export function upsertWhiteboard(storage: Storage, record: WhiteboardRecord) {
  const boards = readWhiteboards(storage);
  const index = boards.findIndex((board) => board.id === record.id);
  if (index >= 0) {
    boards[index] = { ...boards[index], ...record };
  } else {
    boards.unshift(record);
  }
  writeWhiteboards(storage, boards);
  return boards;
}

// ═════════════════════════════════════════════════════════════════════════════
// API remota — pizarras vinculadas a proyectos
// ═════════════════════════════════════════════════════════════════════════════

export async function fetchProjectWhiteboards(
  token: string
): Promise<ProjectWhiteboard[]> {
  const data = await apiFetch<ProjectWhiteboard[]>("/projects/whiteboards", {
    token,
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
