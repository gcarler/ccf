import { describe, it, expect } from "vitest";

import {
  canEditCms,
  canPublishCms,
  canManageSites,
  CmsRole,
} from "./permissions";

const ADMINS: CmsRole[] = ["admin", "administrador", "gestor", "editor", "coordinador", "docente", "pastor"];
const PUBLISHERS: CmsRole[] = ["admin", "administrador", "gestor", "coordinador", "pastor"];
const ALL_ROLES: CmsRole[] = [
  "admin",
  "administrador",
  "gestor",
  "editor",
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
    it.each(ADMINS)("admite rol privilegiado: %s", (role) => {
      expect(canEditCms(role)).toBe(true);
    });

    it.each(NEGATIVE)("rechaza rol no privilegiado: %s", (role) => {
      expect(canEditCms(role)).toBe(false);
    });

    it("admite 'docente' como editor pero no como publicador [edge]", () => {
      expect(canEditCms("docente")).toBe(true);
      expect(canPublishCms("docente")).toBe(false);
    });

    // Regresión: el backend expone platform_role en español (ADMINISTRADOR,
    // GESTOR, EDITOR, LECTOR) y AuthContext lo normaliza a lowercase.
    it("acepta el rol real del Kernel 'administrador' (lowercase de ADMINISTRADOR)", () => {
      expect(canEditCms("administrador")).toBe(true);
      expect(canPublishCms("administrador")).toBe(true);
      expect(canManageSites("administrador")).toBe(true);
      // case-insensitive (normalize hace lowercase) para los tres permisos
      expect(canEditCms("ADMINISTRADOR")).toBe(true);
      expect(canPublishCms("ADMINISTRADOR")).toBe(true);
      expect(canManageSites("ADMINISTRADOR")).toBe(true);
    });

    // Política: GESTOR edita y publica; EDITOR solo edita.
    it("mapea GESTOR como editor+publicador y EDITOR como solo editor", () => {
      expect(canEditCms("gestor")).toBe(true);
      expect(canPublishCms("gestor")).toBe(true);
      expect(canManageSites("gestor")).toBe(true);
      expect(canEditCms("editor")).toBe(true);
      expect(canPublishCms("editor")).toBe(false);
      expect(canManageSites("editor")).toBe(false);
    });

    it("rechaza LECTOR (solo lectura) para edición CMS", () => {
      expect(canEditCms("lector")).toBe(false);
      expect(canPublishCms("lector")).toBe(false);
      expect(canManageSites("lector")).toBe(false);
    });
  });

  describe("canPublishCms", () => {
    it.each(PUBLISHERS)("admite rol publicador: %s", (role) => {
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
    it.each(PUBLISHERS)("admite rol gestor de sitios: %s", (role) => {
      expect(canManageSites(role)).toBe(true);
    });

    it.each(["editor", "docente", "estudiante", "aspirante"])(
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
