import { describe, expect, it } from "vitest";
import { normalizeThumbnailOverrides, resolveThumbnailUrl } from "./thumbnail-overrides";

describe("predicas thumbnail overrides", () => {
  it("normalizes object and previous array CMS forms", () => {
    expect(normalizeThumbnailOverrides({ "video-1": "/cms/one.webp", invalid: 42 })).toEqual({
      "video-1": "/cms/one.webp",
    });
    expect(normalizeThumbnailOverrides([
      { video_id: "video-2", url: "/cms/two.webp" },
      { id: "video-3", image_url: "/cms/three.webp" },
      { video_id: "", url: "/cms/ignored.webp" },
    ])).toEqual({
      "video-2": "/cms/two.webp",
      "video-3": "/cms/three.webp",
    });
  });

  it("uses the CMS image when present and YouTube when absent", () => {
    const video = {
      id: "video-1",
      thumbnail_hq: "https://img.youtube.com/video-1/hqdefault.jpg",
    };
    expect(resolveThumbnailUrl(video, { "video-1": "/api/static/cms/public-site/edited.webp" }))
      .toBe("/api/static/cms/public-site/edited.webp");
    expect(resolveThumbnailUrl(video, {})).toBe(video.thumbnail_hq);
  });
});
