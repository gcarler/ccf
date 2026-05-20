export type TestimonialMediaType = "text" | "image" | "video" | "podcast";
export type NonTextTestimonialMediaType = Exclude<TestimonialMediaType, "text">;

export interface TestimonialMediaAsset {
  id?: number;
  url: string;
  filename?: string | null;
  mime_type?: string | null;
  alt_text?: string | null;
  status?: string | null;
}

export function normalizeTestimonialMediaType(value?: string | null): TestimonialMediaType {
  if (value === "image" || value === "video" || value === "podcast") return value;
  return "text";
}

export function inferTestimonialMediaType(mimeType?: string | null): NonTextTestimonialMediaType | null {
  if (!mimeType) return null;
  if (mimeType.startsWith("image/")) return "image";
  if (mimeType.startsWith("video/")) return "video";
  if (mimeType.startsWith("audio/")) return "podcast";
  return null;
}

export function isCompatibleTestimonialMedia(asset: TestimonialMediaAsset, mediaType?: string | null): boolean {
  const normalized = normalizeTestimonialMediaType(mediaType);
  if (normalized === "text" || asset.status === "archived") return false;
  return inferTestimonialMediaType(asset.mime_type) === normalized;
}

export function activeTestimonialMediaAssets<T extends TestimonialMediaAsset>(
  assets: T[],
  mediaType?: string | null,
  search = "",
  limit = 8,
): T[] {
  const query = search.trim().toLowerCase();
  return assets
    .filter((asset) => {
      if (!isCompatibleTestimonialMedia(asset, mediaType)) return false;
      if (!query) return true;
      return [asset.filename, asset.alt_text, asset.mime_type].some((value) => value?.toLowerCase().includes(query));
    })
    .slice(0, limit);
}
