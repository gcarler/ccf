export interface WhiteboardRecord {
  id: string;
  title: string;
  description?: string;
  created_at: string;
  updated_at?: string;
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
