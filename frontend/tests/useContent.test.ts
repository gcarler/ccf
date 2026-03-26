import { describe, it, expect } from "vitest";
import { mergeContent } from "../src/hooks/useContent";

describe("mergeContent", () => {
  it("merges parsed JSON props into the block", () => {
    const block = {
      page_key: "home_hero",
      content: JSON.stringify({ some_custom_field: "Hola", subtitle: "Mundo" }),
    };

    const result = mergeContent(block);

    expect(result).toMatchObject({
      page_key: "home_hero",
      some_custom_field: "Hola",
      subtitle: "Mundo",
    });
    expect(result?.parsed).toEqual({ some_custom_field: "Hola", subtitle: "Mundo" });
  });

  it("returns original block when content is invalid JSON", () => {
    const block = {
      page_key: "test",
      content: "not-json",
      title: "Keep",
    };

    const result = mergeContent(block);

    expect(result?.title).toBe("Keep");
    expect(result?.parsed).toBe("not-json");
  });

  it("returns null when block is missing", () => {
    expect(mergeContent(undefined)).toBeNull();
  });
});
