import { describe, expect, it } from "vitest";
import { getCmsMediaUrl } from "./media";

describe("getCmsMediaUrl", () => {
  it("returns an empty string for nullish input", () => {
    expect(getCmsMediaUrl(null)).toBe("");
    expect(getCmsMediaUrl(undefined)).toBe("");
  });

  it("passes canonical /api/static/ URLs through unchanged", () => {
    const url = "/api/static/cms/pastores/abc.webp";
    expect(getCmsMediaUrl(url)).toBe(url);
  });

  it("normalises the earlier /static/ form to /api/static/", () => {
    expect(getCmsMediaUrl("/static/cms/pastores/abc.webp")).toBe("/api/static/cms/pastores/abc.webp");
  });

  it("collapses a doubled /api/static/api/static/ prefix (defensive normalisation)", () => {
    expect(getCmsMediaUrl("/api/static/api/static/cms/pastores/abc.webp")).toBe(
      "/api/static/cms/pastores/abc.webp",
    );
  });

  it("passes external/absolute URLs through unchanged", () => {
    const url = "https://cdn.example.com/media/abc.webp";
    expect(getCmsMediaUrl(url)).toBe(url);
  });
});
