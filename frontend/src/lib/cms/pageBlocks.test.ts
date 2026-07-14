import { describe, expect, it } from "vitest";

import { buildCmsPageBlocks } from "./pageBlocks";

describe("buildCmsPageBlocks", () => {
  it("exposes raw props plus parsed and content compatibility fields", () => {
    const blocks = buildCmsPageBlocks([
      {
        section_key: "hero",
        props_json: {
          eyebrow: "Hola",
          title: "Liderazgo",
        },
      },
    ]);

    expect(blocks.hero.eyebrow).toBe("Hola");
    expect(blocks.hero.title).toBe("Liderazgo");
    expect(blocks.hero.parsed).toEqual({
      eyebrow: "Hola",
      title: "Liderazgo",
    });
    expect(blocks.hero.content).toBe(JSON.stringify({
      eyebrow: "Hola",
      title: "Liderazgo",
    }));
  });

  it("skips empty section keys and normalizes invalid payloads", () => {
    const blocks = buildCmsPageBlocks([
      { section_key: "  ", props_json: { a: 1 } },
      { section_key: "feed", props_json: null },
    ]);

    expect(blocks).toEqual({
      feed: {
        parsed: {},
        content: "{}",
      },
    });
  });
});
