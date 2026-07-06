/**
 * Test gate: AGENTS_FRONTEND.md §4 — Paleta SOLO azules
 *
 * Detecta y falla la suite si reaparece cualquier clase de Tailwind
 * construida con la paleta prohibida: indigo, violet, purple, fuchsia.
 *
 * Cubre el patrón completo de utilidades Tailwind que reciben color:
 *   bg-*, text-*, border-*, from-*, to-*, via-*, ring-*,
 *   divide-*, outline-*, decoration-*, placeholder-*,
 *   caret-*, accent-*, fill-*, stroke-*, shadow-*
 *
 * Soporta modificadores múltiples en la utilidad (un solo bloque):
 *   cualquier `-<palabra-o-dígito>` intermedio entre la utilidad
 *   y el color. Ejemplos no-literales: border-{side}, ring-offset,
 *   divide-{axis}, border-t-2, ring-1, outline-offset, etc.
 *
 * Soporta modificadores de estado como prefijo de la clase:
 *   dark:, hover:, group-hover:, focus:, sm:, md:, lg:, xl:, 2xl:,
 *   peer-checked:, aria-*, supports-*, etc. (matchea como substring).
 *
 * Limitación conocida: el regex detecta clases Tailwind con la forma
 * `<util>(-<palabra>)*-<color>-<shade>` pero NO valores hex literales
 * como #7c3aed (violet-600) o #d946ef (fuchsia-500). Las hex prohibidas
 * deben auditarse manualmente en code review. Si se necesita detección
 * automática de hex, añadir un segundo bloque con una lookup table de
 * los hex más comunes de las paletas prohibidas.
 *
 * Cobertura de escaneo: src/ y tests/ del frontend.
 * Fuera de cobertura intencional:
 *   - public/ (assets estáticos, sin Tailwind procesado)
 *   - tailwind.config.ts (define tokens del sistema, no usa paleta prohibida)
 *   - .storybook/, storybook-static/ (builds de Storybook)
 *   - node_modules/, .next/, dist/, build/, coverage/ (vendor/build output)
 * Si se introducen colores prohibidos en esos directorios, este test no
 * los detectará — es intencional por convención del proyecto.
 *
 * Referencia: ccf/AGENTS_FRONTEND.md §4 — Colores prohibidos.
 */
import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const FORBIDDEN_COLORS = ["indigo", "violet", "purple", "fuchsia"] as const;
const COLOR_SHADES = "(50|100|200|300|400|500|600|700|800|900|950)";
const OPACITY_SUFFIX = "(/[0-9]+)?";
const TAILWIND_UTILS =
  "(bg|text|border|from|to|via|ring|divide|outline|decoration|placeholder|caret|accent|fill|stroke|shadow)";
// Permitir modificadores múltiples entre la utilidad y el color:
//   border-{side}, ring-offset, divide-{axis}, border-t-2, ring-1, etc.
const UTIL_MODIFIER = "(-[a-z0-9]+)*";

const FORBIDDEN_PATTERN = new RegExp(
  `\\b${TAILWIND_UTILS}${UTIL_MODIFIER}-(${FORBIDDEN_COLORS.join("|")})-${COLOR_SHADES}${OPACITY_SUFFIX}\\b`,
  "g"
);

const SCAN_ROOTS = ["src", "tests"] as const;
const SCAN_EXTS = [".ts", ".tsx", ".jsx", ".js", ".css", ".mjs", ".cjs"] as const;
const EXCLUDE_DIRS = new Set([
  "node_modules",
  ".next",
  "dist",
  "build",
  "storybook-static",
  ".storybook",
  "coverage",
]);

type Offender = { file: string; line: number; text: string; pattern: string };

function walk(dir: string, acc: string[] = []): string[] {
  let entries: string[];
  try {
    entries = readdirSync(dir);
  } catch {
    return acc;
  }
  for (const entry of entries) {
    if (EXCLUDE_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    let st;
    try {
      st = statSync(full);
    } catch {
      continue;
    }
    if (st.isDirectory()) walk(full, acc);
    else if (SCAN_EXTS.some((ext) => full.endsWith(ext))) acc.push(full);
  }
  return acc;
}

function scanForOffenders(): Offender[] {
  const offenders: Offender[] = [];
  for (const root of SCAN_ROOTS) {
    const files = walk(root);
    for (const file of files) {
      const text = readFileSync(file, "utf8");
      const lines = text.split("\n");
      for (let i = 0; i < lines.length; i++) {
        const matches = lines[i].match(FORBIDDEN_PATTERN);
        if (matches) {
          for (const m of matches) {
            offenders.push({
              file: relative(process.cwd(), file),
              line: i + 1,
              text: lines[i].trim().slice(0, 140),
              pattern: m,
            });
          }
        }
      }
    }
  }
  return offenders;
}

describe("AGENTS_FRONTEND.md §4 — paleta solo azules", () => {
  it("no debe haber clases Tailwind con colores prohibidos (indigo/violet/purple/fuchsia)", () => {
    const offenders = scanForOffenders();
    if (offenders.length > 0) {
      const listing = offenders
        .map((o) => `  ${o.file}:${o.line}  →  ${o.text}   [match: ${o.pattern}]`)
        .join("\n");
      throw new Error(
        `AGENTS_FRONTEND.md §4 violada — clases con paleta prohibida detectadas:\n${listing}\n\n` +
          `Reemplaza por tokens azules (blue-* / hsl(var(--primary))) o por la paleta ` +
          `categórica permitida: emerald-*, teal-*, cyan-*, amber-*, red-*, rose-*.\n` +
          `Ver ccf/AGENTS_FRONTEND.md §4 para referencia.`,
      );
    }
    expect(offenders).toEqual([]);
  });
});
