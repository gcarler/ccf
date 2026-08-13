export interface ThumbnailVideo {
  id: string;
  thumbnail_hq: string;
}

export type ThumbnailOverrides = Record<string, string>;

/** Accepts both the object form and the array form used by older CMS drafts. */
export function normalizeThumbnailOverrides(value: unknown): ThumbnailOverrides {
  if (Array.isArray(value)) {
    return Object.fromEntries(
      value.flatMap((item) => {
        if (!item || typeof item !== "object") return [];
        const row = item as Record<string, unknown>;
        const id = typeof row.video_id === "string"
          ? row.video_id
          : typeof row.id === "string" ? row.id : "";
        const url = typeof row.url === "string"
          ? row.url
          : typeof row.image_url === "string" ? row.image_url : "";
        return id.trim() ? [[id.trim(), url]] : [];
      }),
    );
  }
  if (!value || typeof value !== "object") return {};
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).flatMap(([id, url]) =>
      typeof url === "string" && id.trim() ? [[id.trim(), url]] : []
    ),
  );
}

export function resolveThumbnailUrl(video: ThumbnailVideo, overrides: ThumbnailOverrides): string {
  return overrides[video.id] || video.thumbnail_hq;
}
