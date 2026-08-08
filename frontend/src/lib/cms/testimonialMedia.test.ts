import { describe, it, expect } from "vitest";
import {
  normalizeTestimonialMediaType,
  inferTestimonialMediaType,
  isCompatibleTestimonialMedia,
  activeTestimonialMediaAssets,
  type TestimonialMediaAsset,
} from "./testimonialMedia";

const asset = (over: Partial<TestimonialMediaAsset> = {}): TestimonialMediaAsset => ({
  url: "/x",
  ...over,
});

describe("normalizeTestimonialMediaType", () => {
  it("passes through known non-text values", () => {
    expect(normalizeTestimonialMediaType("image")).toBe("image");
    expect(normalizeTestimonialMediaType("video")).toBe("video");
    expect(normalizeTestimonialMediaType("podcast")).toBe("podcast");
  });

  it("defaults unknown/null/empty to text", () => {
    expect(normalizeTestimonialMediaType("text")).toBe("text");
    expect(normalizeTestimonialMediaType(null)).toBe("text");
    expect(normalizeTestimonialMediaType(undefined)).toBe("text");
    expect(normalizeTestimonialMediaType("nope")).toBe("text");
  });
});

describe("inferTestimonialMediaType", () => {
  it("infers image/video/podcast by mime prefix", () => {
    expect(inferTestimonialMediaType("image/png")).toBe("image");
    expect(inferTestimonialMediaType("video/mp4")).toBe("video");
    expect(inferTestimonialMediaType("audio/mpeg")).toBe("podcast");
  });

  it("returns null for empty or unknown mime", () => {
    expect(inferTestimonialMediaType(null)).toBeNull();
    expect(inferTestimonialMediaType(undefined)).toBeNull();
    expect(inferTestimonialMediaType("application/pdf")).toBeNull();
  });
});

describe("isCompatibleTestimonialMedia", () => {
  it("rejects text mediaType (not attachable)", () => {
    expect(isCompatibleTestimonialMedia(asset({ mime_type: "image/png" }), "text")).toBe(false);
  });

  it("rejects archived assets regardless of mime", () => {
    expect(isCompatibleTestimonialMedia(asset({ mime_type: "image/png", status: "archived" }), "image")).toBe(false);
  });

  it("accepts when inferred media matches the requested type", () => {
    expect(isCompatibleTestimonialMedia(asset({ mime_type: "video/mp4" }), "video")).toBe(true);
    expect(isCompatibleTestimonialMedia(asset({ mime_type: "audio/mpeg" }), "podcast")).toBe(true);
  });

  it("rejects when inferred media differs from the requested type", () => {
    expect(isCompatibleTestimonialMedia(asset({ mime_type: "image/png" }), "video")).toBe(false);
    expect(isCompatibleTestimonialMedia(asset({ mime_type: "video/mp4" }), "image")).toBe(false);
  });

  it("defaults to text (incompatible) when mediaType is omitted/unknown", () => {
    expect(isCompatibleTestimonialMedia(asset({ mime_type: "image/png" }), null)).toBe(false);
    expect(isCompatibleTestimonialMedia(asset({ mime_type: "image/png" }), "nope")).toBe(false);
  });
});

describe("activeTestimonialMediaAssets", () => {
  const assets: TestimonialMediaAsset[] = [
    asset({ id: 1, mime_type: "image/png", filename: "a.png", alt_text: "Alt A" }),
    asset({ id: 2, mime_type: "video/mp4", filename: "b.mp4" }),
    asset({ id: 3, mime_type: "image/jpeg", status: "archived", filename: "old.jpg" }),
    asset({ id: 4, mime_type: "audio/mpeg", filename: "c.mp3" }),
  ];

  it("returns compatible assets (filters archived and text-mismatch)", () => {
    const out = activeTestimonialMediaAssets(assets, "image");
    expect(out.map((a) => a.id)).toEqual([1]);
  });

  it("returns video assets for video mediaType", () => {
    expect(activeTestimonialMediaAssets(assets, "video").map((a) => a.id)).toEqual([2]);
  });

  it("returns [] for text mediaType (no compatible assets)", () => {
    expect(activeTestimonialMediaAssets(assets, "text")).toEqual([]);
  });

  it("filters by search term across filename/alt_text/mime_type", () => {
    const out = activeTestimonialMediaAssets(assets, "image", "a");
    expect(out.map((a) => a.id)).toEqual([1]); // match filename "a.png" or alt "Alt A"

    expect(activeTestimonialMediaAssets(assets, "video", "b").map((a) => a.id)).toEqual([2]);
  });

  it("returns [] when no asset matches the search", () => {
    expect(activeTestimonialMediaAssets(assets, "image", "zzz")).toEqual([]);
  });

  it("respects the limit argument", () => {
    const many: TestimonialMediaAsset[] = Array.from({ length: 12 }, (_, i) =>
      asset({ id: i + 1, mime_type: "image/png", filename: `f${i}.png` }),
    );
    expect(activeTestimonialMediaAssets(many, "image", "", 12)).toHaveLength(12);
    expect(activeTestimonialMediaAssets(many, "image", "", 5)).toHaveLength(5);
    expect(activeTestimonialMediaAssets(many, "image", "", 8)).toHaveLength(8);
  });

  it("uses default limit 8", () => {
    const many: TestimonialMediaAsset[] = Array.from({ length: 12 }, (_, i) =>
      asset({ id: i + 1, mime_type: "image/png", filename: `f${i}.png` }),
    );
    expect(activeTestimonialMediaAssets(many, "image")).toHaveLength(8);
  });
});
