import { describe, expect, it } from "vitest";
import { parseDependencyType } from "./ProjectGanttView";

describe("parseDependencyType", () => {
  it.each(["FS", "SS", "FF", "SF"] as const)("accepts the backend dependency type %s", (value) => {
    expect(parseDependencyType(value)).toBe(value);
  });

  it.each(["", "fs", "INVALID"])("rejects unsupported dependency type %s", (value) => {
    expect(parseDependencyType(value)).toBeNull();
  });
});
