import { describe, expect, it, vi } from "vitest";
import {
  diffArray,
  diffObject,
  diffPageVersionSnapshots,
  diffWords,
  diffValue,
  filterSemanticPropDiffs,
  humanizeFieldName,
  type PageVersionSnapshot,
  type SectionSnapshot,
} from "./versionDiff";

// ── diffWords (LCS) ────────────────────────────────────────────────────

describe("diffWords", () => {
  it("returns the same string as all-unchanged when inputs match", () => {
    const tokens = diffWords("hello world", "hello world");
    expect(tokens.every((t) => t.type === "unchanged")).toBe(true);
    expect(tokens.map((t) => t.value).join("")).toBe("hello world");
  });

  it("marks pure addition correctly", () => {
    const tokens = diffWords("hello", "hello world");
    const added = tokens.filter((t) => t.type === "added").map((t) => t.value);
    expect(added.join("")).toBe(" world");
  });

  it("marks pure removal correctly", () => {
    const tokens = diffWords("hello world", "hello");
    const removed = tokens.filter((t) => t.type === "removed").map((t) => t.value);
    expect(removed.join("")).toBe(" world");
  });

  it("preserves the visible structure when one word changes", () => {
    const tokens = diffWords("the quick brown fox", "the slow brown fox");
    const added = tokens.filter((t) => t.type === "added").map((t) => t.value);
    const removed = tokens.filter((t) => t.type === "removed").map((t) => t.value);
    expect(added.join("")).toBe("slow");
    expect(removed.join("")).toBe("quick");
  });

  it("reconstructs the original (before) and updated (after) strings", () => {
    const a = "Bienvenidos a la iglesia";
    const b = "Bienvenidos a la comunidad";
    const tokens = diffWords(a, b);
    const reconstructedBefore = tokens
      .filter((t) => t.type !== "added")
      .map((t) => t.value)
      .join("");
    const reconstructedAfter = tokens
      .filter((t) => t.type !== "removed")
      .map((t) => t.value)
      .join("");
    expect(reconstructedBefore).toBe(a);
    expect(reconstructedAfter).toBe(b);
  });

  it("handles empty strings", () => {
    expect(diffWords("", "")).toEqual([]);
    expect(diffWords("", "new").every((t) => t.type === "added")).toBe(true);
    expect(diffWords("old", "").every((t) => t.type === "removed")).toBe(true);
  });

  it("keeps trailing punctuation glued to its word", () => {
    const tokens = diffWords("Hola, mundo.", "Hola, amigos.");
    const beforeText = tokens
      .filter((t) => t.type !== "added")
      .map((t) => t.value)
      .join("");
    expect(beforeText).toBe("Hola, mundo.");
  });
});

// ── diffValue (typed) ─────────────────────────────────────────────────

describe("diffValue", () => {
  it("treats equal scalars as unchanged", () => {
    expect(diffValue(1, 1).kind).toBe("unchanged");
    expect(diffValue("x", "x").kind).toBe("unchanged");
    expect(diffValue(true, true).kind).toBe("unchanged");
  });

  it("flags different scalars as changed", () => {
    expect(diffValue(1, 2).kind).toBe("changed");
    expect(diffValue("a", "b").kind).toBe("changed");
  });

  it("flags missing-before as added", () => {
    const d = diffValue(undefined, "hi");
    expect(d.kind).toBe("added");
  });

  it("flags missing-after as removed", () => {
    const d = diffValue("hi", undefined);
    expect(d.kind).toBe("removed");
  });

  it("diffs strings with word tokens", () => {
    const d = diffValue("old text", "new text");
    expect(d.kind).toBe("changed");
    expect(Array.isArray(d.tokens)).toBe(true);
  });
});

// ── diffObject (recursive) ────────────────────────────────────────────

describe("diffObject", () => {
  it("only returns keys that changed", () => {
    const d = diffObject({ a: 1, b: 2 }, { a: 1, b: 3 });
    expect(Object.keys(d).sort()).toEqual(["b"]);
    expect(d.b.kind).toBe("changed");
  });

  it("flags keys that exist on only one side", () => {
    const d = diffObject({ a: 1 }, { a: 1, b: 2 });
    expect(d.b.kind).toBe("added");
  });

  it("recurses into nested objects", () => {
    const d = diffObject(
      { seo: { title: "A", description: "x" } },
      { seo: { title: "B", description: "x" } },
    );
    expect(d.seo).toBeDefined();
    // nested object diff yields a synthetic changed
    expect(d.seo.kind).toBe("changed");
  });

  it("treats two empty objects as unchanged", () => {
    expect(diffObject({}, {})).toEqual({});
  });
});

// ── diffArray (stable-key) ────────────────────────────────────────────

describe("diffArray", () => {
  it("uses id as stable key when present", () => {
    const a = [
      { id: "a", title: "First" },
      { id: "b", title: "Second" },
    ];
    const b = [
      { id: "b", title: "Second" },
      { id: "a", title: "First" },
    ];
    const d = diffArray(a, b);
    // Order changed but contents match → still "changed" because
    // we always record the array delta. The per-item diff is
    // what the UI uses to render "moved" badges.
    expect(d.kind).toBe("changed");
  });

  it("falls back to positional when no stable key", () => {
    const a = ["x", "y", "z"];
    const b = ["x", "y", "z"];
    expect(diffArray(a, b).kind).toBe("unchanged");

    const c = diffArray(["x", "y"], ["x", "z"]);
    expect(c.kind).toBe("changed");
  });
});

// ── Section-level diff ────────────────────────────────────────────────

describe("section diff (via diffPageVersionSnapshots)", () => {
  const section = (overrides: Partial<SectionSnapshot> = {}): SectionSnapshot => ({
    id: overrides.id ?? "sec-1",
    section_key: overrides.section_key ?? "hero",
    type: overrides.type ?? "hero",
    props_json: overrides.props_json ?? { title: "Welcome" },
    sort_order: overrides.sort_order ?? 0,
    is_visible: overrides.is_visible ?? true,
    status: overrides.status ?? "active",
  });

  it("detects an added section", () => {
    const before: PageVersionSnapshot = { page: {}, sections: [] };
    const after: PageVersionSnapshot = {
      page: {},
      sections: [section({ section_key: "new", id: "new" })],
    };
    const diff = diffPageVersionSnapshots(before, after);
    expect(diff.sections).toHaveLength(1);
    expect(diff.sections[0].status).toBe("added");
    expect(diff.summary.sectionsAdded).toBe(1);
  });

  it("detects a removed section", () => {
    const before: PageVersionSnapshot = {
      page: {},
      sections: [section({ section_key: "gone", id: "gone" })],
    };
    const after: PageVersionSnapshot = { page: {}, sections: [] };
    const diff = diffPageVersionSnapshots(before, after);
    expect(diff.sections[0].status).toBe("removed");
    expect(diff.summary.sectionsRemoved).toBe(1);
  });

  it("detects reorder-only change as a separate semantic category", () => {
    const before: PageVersionSnapshot = {
      page: {},
      sections: [
        section({ id: "a", section_key: "a", sort_order: 0 }),
        section({ id: "b", section_key: "b", sort_order: 1 }),
      ],
    };
    const after: PageVersionSnapshot = {
      page: {},
      sections: [
        section({ id: "b", section_key: "b", sort_order: 0 }),
        section({ id: "a", section_key: "a", sort_order: 1 }),
      ],
    };
    const diff = diffPageVersionSnapshots(before, after);
    expect(diff.sections.every((s) => s.status === "reordered")).toBe(true);
    expect(diff.summary.sectionsReordered).toBe(2);
  });

  it("detects a modified section with prop diffs", () => {
    const before: PageVersionSnapshot = {
      page: {},
      sections: [
        section({
          section_key: "hero",
          id: "hero-1",
          props_json: { title: "Old Title", body: "Body" },
        }),
      ],
    };
    const after: PageVersionSnapshot = {
      page: {},
      sections: [
        section({
          section_key: "hero",
          id: "hero-1",
          props_json: { title: "New Title", body: "Body" },
        }),
      ],
    };
    const diff = diffPageVersionSnapshots(before, after);
    expect(diff.sections[0].status).toBe("modified");
    expect(diff.sections[0].prop_diffs?.title.kind).toBe("changed");
    expect(diff.sections[0].prop_diffs?.body).toBeUndefined();
  });

  it("matches by section_key (not id) so renames stay stable", () => {
    const before: PageVersionSnapshot = {
      page: {},
      sections: [section({ id: "uuid-1", section_key: "main-cta" })],
    };
    const after: PageVersionSnapshot = {
      page: {},
      sections: [
        section({
          id: "uuid-2", // different uuid
          section_key: "main-cta", // same key
          props_json: { title: "Welcome (updated)" },
        }),
      ],
    };
    const diff = diffPageVersionSnapshots(before, after);
    expect(diff.sections[0].status).toBe("modified");
    expect(diff.sections[0].prop_diffs?.title.kind).toBe("changed");
  });

  it("preserves render order: modifications appear in their new position", () => {
    const before: PageVersionSnapshot = {
      page: {},
      sections: [
        section({ id: "a", section_key: "a", sort_order: 0, props_json: { title: "A" } }),
        section({ id: "b", section_key: "b", sort_order: 1, props_json: { title: "B" } }),
      ],
    };
    const after: PageVersionSnapshot = {
      page: {},
      sections: [
        section({ id: "b", section_key: "b", sort_order: 0, props_json: { title: "B-new" } }),
        section({ id: "a", section_key: "a", sort_order: 1, props_json: { title: "A" } }),
      ],
    };
    const diff = diffPageVersionSnapshots(before, after);
    expect(diff.sections[0].section_key).toBe("b");
    expect(diff.sections[1].section_key).toBe("a");
  });

  it("flags visibility changes as their own semantic status", () => {
    const before: PageVersionSnapshot = {
      page: {},
      sections: [section({ id: "x", section_key: "x", is_visible: true })],
    };
    const after: PageVersionSnapshot = {
      page: {},
      sections: [section({ id: "x", section_key: "x", is_visible: false })],
    };
    const diff = diffPageVersionSnapshots(before, after);
    expect(diff.sections[0].status).toBe("visibility-changed");
  });

  it("surfaces orphan sections (no section_key, no id) with synthetic keys", () => {
    // Sections without any stable identifier on either side still get
    // a row in the diff — the synthetic key carries a side-specific
    // index so the UI can disambiguate multiple orphans. We stub
    // ``console.warn`` to keep test output clean and assert the
    // warning is emitted.
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    try {
      const before: PageVersionSnapshot = {
        page: {},
        // No section_key, no id.
        sections: [
          { type: "rich_text", props_json: { title: "Ghost 1" }, sort_order: 0 } as SectionSnapshot,
        ],
      };
      const after: PageVersionSnapshot = {
        page: {},
        sections: [
          { type: "rich_text", props_json: { title: "Ghost 1" }, sort_order: 0 } as SectionSnapshot,
          { type: "rich_text", props_json: { title: "Ghost 2" }, sort_order: 1 } as SectionSnapshot,
        ],
      };
      const diff = diffPageVersionSnapshots(before, after);
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining("3 section(s) have no section_key/id"),
      );
      // Both sides contribute orphan rows. The UI filter is what
      // collapses them visually; here we just verify the API gives
      // us one row per orphan position.
      expect(diff.sections.length).toBeGreaterThan(0);
      const orphanRows = diff.sections.filter((s) =>
        s.section_key.startsWith("(sin clave"),
      );
      expect(orphanRows.length).toBeGreaterThan(0);
    } finally {
      warnSpy.mockRestore();
    }
  });
});

// ── Page-meta diff ────────────────────────────────────────────────────

describe("page meta diff", () => {
  it("flags title changes with word-level tokens", () => {
    const diff = diffPageVersionSnapshots(
      { page: { title: "Iglesia" }, sections: [] },
      { page: { title: "Iglesia Central" }, sections: [] },
    );
    expect(diff.pageMeta.title.kind).toBe("changed");
    expect(diff.pageMeta.title.tokens?.some((t) => t.type === "added")).toBe(true);
    expect(diff.summary.titleChanged).toBe(true);
  });

  it("counts seo field changes", () => {
    const diff = diffPageVersionSnapshots(
      {
        page: { seo_json: { meta_title: "T", meta_description: "D" } },
        sections: [],
      },
      {
        page: { seo_json: { meta_title: "T2", meta_description: "D" } },
        sections: [],
      },
    );
    expect(diff.summary.seoFieldsChanged).toBe(1);
    expect(diff.pageMeta.seo.meta_title.kind).toBe("changed");
    expect(diff.pageMeta.seo.meta_description).toBeUndefined();
  });
});

// ── Pretty printers ───────────────────────────────────────────────────

describe("humanizeFieldName + filterSemanticPropDiffs", () => {
  it("humanizes snake_case and camelCase", () => {
    expect(humanizeFieldName("meta_description")).toBe("Meta Description");
    expect(humanizeFieldName("ctaHref")).toBe("Cta Href");
    expect(humanizeFieldName("image_url")).toBe("Image Url");
  });

  it("filters to curated fields first, then extras alphabetically", () => {
    const propDiffs = {
      body: { kind: "changed" as const },
      title: { kind: "changed" as const },
      custom_marker: { kind: "changed" as const },
      cta_label: { kind: "changed" as const },
    };
    const rows = filterSemanticPropDiffs("hero", propDiffs);
    expect(rows.map((r) => r.key)).toEqual([
      "title",
      "body",
      "cta_label",
      "custom_marker",
    ]);
  });
});
