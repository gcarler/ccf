import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const FORBIDDEN_COLORS = ["indigo", "violet", "purple", "fuchsia"] as const;
const COLOR_SHADES = "(50|100|200|300|400|500|600|700|800|900|950)";
const TAILWIND_UTILS =
  "(bg|text|border|from|to|via|ring|divide|outline|decoration|placeholder|caret|accent|fill|stroke|shadow)";
const UTIL_MODIFIER = "(-[a-z0-9]+)*";
const FORBIDDEN_CLASS_PATTERN = new RegExp(
  `\\b${TAILWIND_UTILS}${UTIL_MODIFIER}-(${FORBIDDEN_COLORS.join("|")})-${COLOR_SHADES}(?:/[0-9]+)?\\b`,
  "g",
);
const FORBIDDEN_HEX_PATTERN = /#(?:d946ef|7c3aed)\b/gi;
const FORBIDDEN_SEMANTIC_TOKEN_PATTERN = /domain-fuchsia\b/g;

const SCAN_ROOT = "src";
const SCAN_EXTS = [".ts", ".tsx", ".jsx", ".js", ".css", ".mjs", ".cjs"] as const;
const EXCLUDE_DIRS = new Set([
  "node_modules",
  ".next",
  "dist",
  "build",
  "coverage",
  "storybook-static",
  ".storybook",
]);

// These files define persisted/canonical color options rather than rendered UI classes.
const EXCLUDED_FILES = new Set([
  "src/app/globals.css",
  "src/design/tokens-semantic.ts",
  "src/lib/projects/palette.ts",
  "src/lib/projects/palette.test.ts",
]);

type Offender = { file: string; line: number; match: string };

function walk(dir: string, files: string[] = []): string[] {
  let entries: string[];
  try {
    entries = readdirSync(dir);
  } catch {
    return files;
  }

  for (const entry of entries) {
    if (EXCLUDE_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    let stats;
    try {
      stats = statSync(full);
    } catch {
      continue;
    }
    if (stats.isDirectory()) walk(full, files);
    else if (SCAN_EXTS.some((extension) => full.endsWith(extension))) files.push(full);
  }
  return files;
}

function scanForOffenders(): Offender[] {
  const offenders: Offender[] = [];
  for (const file of walk(SCAN_ROOT)) {
    const relativeFile = relative(process.cwd(), file);
    if (EXCLUDED_FILES.has(relativeFile)) continue;

    const lines = readFileSync(file, "utf8").split("\n");
    lines.forEach((line, index) => {
      const matches = [
        ...(line.match(FORBIDDEN_CLASS_PATTERN) ?? []),
        ...(line.match(FORBIDDEN_HEX_PATTERN) ?? []),
        ...(line.match(FORBIDDEN_SEMANTIC_TOKEN_PATTERN) ?? []),
      ];
      for (const match of matches) {
        offenders.push({ file: relativeFile, line: index + 1, match });
      }
    });
  }
  return offenders;
}

describe("CCF frontend palette regression", () => {
  it("does not reintroduce forbidden Tailwind colors or legacy violet/fuchsia hex values", () => {
    const offenders = scanForOffenders();
    expect(offenders, offenders.map((item) => `${item.file}:${item.line} ${item.match}`).join("\n")).toEqual([]);
  });
});
