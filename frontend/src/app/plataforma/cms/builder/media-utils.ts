export type SelectedMedia = { url: string; media_id: string | number };

const MEDIA_URL_KEYS = new Set(["bg_image", "image_url", "url", "src", "photo_url", "thumbnail_url"]);

function attachSelectedMediaId(value: unknown, selected: SelectedMedia): unknown {
  if (Array.isArray(value)) return value.map((item) => attachSelectedMediaId(item, selected));
  if (!value || typeof value !== "object") return value;

  const object = value as Record<string, unknown>;
  const next: Record<string, unknown> = {};
  let matched = false;
  for (const [key, child] of Object.entries(object)) {
    if (key === "__cms_json" && typeof child === "string") {
      try {
        next[key] = JSON.stringify(attachSelectedMediaId(JSON.parse(child), selected), null, 2);
      } catch {
        next[key] = child;
      }
      continue;
    }
    next[key] = attachSelectedMediaId(child, selected);
    matched ||= MEDIA_URL_KEYS.has(key) && child === selected.url;
  }
  if (matched) next.media_id = selected.media_id;
  return next;
}

export function preserveSelectedMediaId(data: { content: unknown[] }, selected: SelectedMedia): { content: unknown[] } {
  return attachSelectedMediaId(data, selected) as { content: unknown[] };
}
