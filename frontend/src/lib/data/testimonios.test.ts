import { describe, it, expect } from "vitest";
import type { Testimonial } from "./testimonios";

describe("data/testimonios (interface)", () => {
  it("logoUrl: puede construir un Testimonial válido", () => {
    const t: Testimonial = {
      id: 1,
      content: "Amazing grace",
      emotion: "joyful",
      media_type: "image",
      media_url: "https://x/img.png",
      image_url: "https://x/img.png",
      video_url: null,
      podcast_url: null,
      author: { id: 2, username: "ana", role: "member", avatarUrl: "/a.png" },
      is_approved: true,
      show_on_home: true,
    };
    expect(t.id).toBe(1);
    expect(t.content).toBe("Amazing grace");
    expect(t.author?.username).toBe("ana");
  });

  it("campos opcionales pueden estar ausentes", () => {
    const t: Testimonial = { id: 1, content: "x" };
    expect(t.media_type).toBeUndefined();
    expect(t.author).toBeUndefined();
    expect(t.is_approved).toBeUndefined();
  });

  it("media_type admite string personalizado", () => {
    const t: Testimonial = { id: 1, content: "", media_type: "custom-format" };
    expect(t.media_type).toBe("custom-format");
  });
});
