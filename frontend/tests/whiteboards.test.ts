import { describe, expect, it } from "vitest";
import { normalizeWhiteboardRecord, whiteboardCanvasKey } from "../src/lib/whiteboards";

describe("whiteboard helpers", () => {
  it("normalizes valid local records", () => {
    expect(normalizeWhiteboardRecord({
      id: 123,
      title: "Mapa",
      description: "Flujo",
      created_at: "2026-05-18T00:00:00.000Z",
    })).toMatchObject({
      id: "123",
      title: "Mapa",
      description: "Flujo",
    });
  });

  it("rejects incomplete local records", () => {
    expect(normalizeWhiteboardRecord({ id: "x" })).toBeNull();
  });

  it("uses a stable canvas storage key", () => {
    expect(whiteboardCanvasKey("local-1")).toBe("ccf_whiteboard:local-1:canvas");
  });
});
