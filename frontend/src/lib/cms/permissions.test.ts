import { describe, it, expect } from "vitest";

import {
  canEditCms,
  canPublishCms,
  canManageSites,
  CmsRole,
} from "./permissions";

const ADMINS: CmsRole[] = ["admin", "coordinador", "docente", "pastor"];
const PUBLISHERS: CmsRole[] = ["admin", "coordinador", "pastor"];
const ALL_ROLES: CmsRole[] = [
  "admin",
  "coordinador",
  "docente",
  "pastor",
  "estudiante",
  "aspirante",
];

const NEGATIVE: Array<string | null | undefined> = [
  null,
  undefined,
  "",
  "estudiante",
  "aspirante",
  "visitante",
  "role-inexistente",
];

describe("cms/permissions", () => {
  describe("canEditCms", () => {
    it.each(ADMINS)("adminite rol privilegiado: %s", (role) => {
      expect(canEditCms(role)).toBe(true);
    });

    it.each(NEGATIVE)("rechaza rol no privilegiado: %s", (role) => {
      expect(canEditCms(role)).toBe(false);
    });

    it("no admite 'docente' como publicador [edge]", () => {
      expect(canEditCms("docente")).toBe(true);
    });
  });

  describe("canPublishCms", () => {
    it.each(PUBLISHERS)("adminite rol publicador: %s", (role) => {
      expect(canPublishCms(role)).toBe(true);
    });

    it.each(ALL_ROLES.filter((r) => !PUBLISHERS.includes(r)))(
      "rechaza rol sin permiso de publicación: %s",
      (role) => {
        expect(canPublishCms(role)).toBe(false);
      }
    );
  });

  describe("canManageSites", () => {
    it.each(PUBLISHERS)("adminite rol gestor de sitios: %s", (role) => {
      expect(canManageSites(role)).toBe(true);
    });

    it.each(["docente", "estudiante", "aspirante"])(
      "rechaza rol sin gestión de sitios: %s",
      (role) => {
        expect(canManageSites(role)).toBe(false);
      }
    );
  });

  describe("normalización (case + whitespace)", () => {
    it("admite mayúsculas mixtas", () => {
      expect(canEditCms("Admin")).toBe(true);
      expect(canPublishCms("COORDINADOR")).toBe(true);
      expect(canManageSites(" PaStOr ")).toBe(true);
    });

    it("rechaza con espacios extremos y case errado", () => {
      expect(canPublishCms(" admin ")).toBe(true);
      expect(canPublishCms("  docente  ")).toBe(false);
    });

    it("rechaza null/undefined/empty de forma determinista", () => {
      expect(canEditCms(null)).toBe(false);
      expect(canPublishCms(undefined)).toBe(false);
      expect(canManageSites("")).toBe(false);
    });
  });
});
