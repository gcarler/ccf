import { describe, it, expect } from "vitest";
import { sanitizeCmsHtml } from "./sanitize";

describe("sanitizeCmsHtml", () => {
  it("returns an empty string for nullish/empty input", () => {
    expect(sanitizeCmsHtml("")).toBe("");
    expect(sanitizeCmsHtml(undefined as unknown as string)).toBe("");
    expect(sanitizeCmsHtml(null as unknown as string)).toBe("");
  });

  it("preserves allowed formatting tags", () => {
    const out = sanitizeCmsHtml("<p>Hola <strong>mundo</strong> <em>!</em></p>");
    expect(out).toContain("<p>");
    expect(out).toContain("<strong>mundo</strong>");
    expect(out).toContain("<em>!</em>");
  });

  it("preserves headings and lists", () => {
    const out = sanitizeCmsHtml("<h2>T</h2><ul><li>a</li><li>b</li></ul>");
    expect(out).toContain("<h2>T</h2>");
    expect(out).toContain("<ul><li>a</li><li>b</li></ul>");
  });

  it("preserves images with allowed attributes and drops disallowed ones", () => {
    const out = sanitizeCmsHtml('<img src="/x.png" alt="alt" onclick="evil()" loading="lazy" />');
    expect(out).toContain('src="/x.png"');
    expect(out).toContain('alt="alt"');
    expect(out).toContain('loading="lazy"');
    expect(out).not.toContain("onclick");
  });

  it("removes dangerous tags: script, iframe, style", () => {
    const out = sanitizeCmsHtml(
      "<p>texto</p><script>alert(1)</script><iframe src=evil></iframe><style>body{}</style>",
    );
    expect(out).toContain("<p>texto</p>");
    expect(out).not.toContain("<script");
    expect(out).not.toContain("<iframe");
    expect(out).not.toContain("<style");
  });

  it("allows data-* attributes on div, blocks arbitrary attributes", () => {
    const out = sanitizeCmsHtml('<div data-controller="tabs" tabindex="0"><span data-x="1">.</span></div>');
    expect(out).toContain('data-controller="tabs"');
    expect(out).toContain('data-x="1"');
    expect(out).not.toContain("tabindex");
  });

  it("forces rel=noopener noreferrer on anchors and keeps target/href", () => {
    const out = sanitizeCmsHtml('<a href="https://example.com" target="_blank">ir</a>');
    expect(out).toContain('href="https://example.com"');
    expect(out).toContain('target="_blank"');
    expect(out).toContain('rel="noopener noreferrer"');
  });

  it("strips javascript: schemes from href", () => {
    const out = sanitizeCmsHtml('<a href="javascript:alert(1)">x</a>');
    expect(out).not.toContain("javascript:");
  });

  it("preserves span with data-* but drops arbitrary span attrs", () => {
    const out = sanitizeCmsHtml('<span data-id="1" style="color:red">t</span>');
    expect(out).toContain('data-id="1"');
    expect(out).not.toContain("style");
  });

  it("keeps table semantics (colspan/rowspan) and drops other attrs on td", () => {
    const out = sanitizeCmsHtml('<table><tbody><tr><td colspan="2" width="10">.</td></tr></tbody></table>');
    expect(out).toContain('colspan="2"');
    expect(out).not.toContain('width="10"');
  });

  it("discards unknown tags but keeps inner text", () => {
    const out = sanitizeCmsHtml("<marquee>ticks</marquee>");
    expect(out).toBe("ticks");
  });
});
