import { describe, it, expect } from "vitest";

import {
  SITE_BLOCKS,
  CIVIC_BLOCKS,
  SITE_EVENTS_BLOCK_KEY,
  SITE_MEDIA_BLOCK_KEY,
  CmsBlockDefinition,
} from "./blocks";
import { SITE_KEY } from "@/lib/site-config";

const ALL_BLOCKS: CmsBlockDefinition[] = [...SITE_BLOCKS, ...CIVIC_BLOCKS];

const KNOWN_PAGES = [
  "*",
  "/",
  "/bienvenida",
  "/boletin",
  "/conocer-a-jesus",
  "/cursos",
  "/eventos",
  "/nosotros",
  "/pastores",
  "/plataforma/community/announcements",
  "/predicas",
  "/privacy",
  "/sedes",
  "/testimonios",
];

describe("blocks.ts — integridad de datos", () => {
  it("SITE_BLOCKS y CIVIC_BLOCKS son arreglos no vacíos", () => {
    expect(SITE_BLOCKS.length).toBeGreaterThan(0);
    expect(CIVIC_BLOCKS.length).toBeGreaterThan(0);
  });

  it("toda definición tiene key/label/description/page de texto no vacío", () => {
    for (const block of ALL_BLOCKS) {
      expect(block.key, `key para "${block.label}"`).toBeTruthy();
      expect(block.label.trim().length, `label de "${block.key}"`).toBeGreaterThan(0);
      expect(block.description.trim().length, `description de "${block.key}"`).toBeGreaterThan(0);
      expect(block.page, `page de "${block.key}"`).toBeTruthy();
    }
  });

  it("las claves son únicas entre todos los bloques", () => {
    const keys = ALL_BLOCKS.map((b) => b.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("las claves de SITE_BLOCKS llevan prefijo del SITE_KEY", () => {
    for (const block of SITE_BLOCKS) {
      expect(block.key.startsWith(`${SITE_KEY}_`), block.key).toBe(true);
    }
  });

  it("las páginas referenciadas están entre las rutas conocidas", () => {
    for (const block of ALL_BLOCKS) {
      expect(KNOWN_PAGES, `${block.key} apunta a "${block.page}"`).toContain(block.page);
    }
  });

  it("todo bloque define una muestra (sample) no vacía", () => {
    for (const block of ALL_BLOCKS) {
      expect(block.sample, block.key).toBeTruthy();
      expect(typeof block.sample, block.key).toBe("object");
    }
  });

  it("las claves especiales de eventos y media siguen el prefijo del sitio", () => {
    expect(SITE_EVENTS_BLOCK_KEY).toBe(`${SITE_KEY}_public_events`);
    expect(SITE_MEDIA_BLOCK_KEY).toBe(`${SITE_KEY}_media_gallery`);
  });

  it("las claves de eventos/media no colisionan con claves definidas", () => {
    const keys = ALL_BLOCKS.map((b) => b.key);
    expect(keys).not.toContain(SITE_EVENTS_BLOCK_KEY);
    expect(keys).not.toContain(SITE_MEDIA_BLOCK_KEY);
  });
});