import { describe, it, expect } from "vitest";

import {
  evaluateProtectedRouteAccess,
  type ProtectedRouteAccessResult,
} from "./protectedRouteAccess";

const noPermissions = () => false;
const permFor = (allowed: string[]) => (p: string) => allowed.includes(p);

describe("protectedRouteAccess — evaluateProtectedRouteAccess", () => {
  describe("rama permissions (tiene prioridad sobre roles)", () => {
    it("con al menos un permiso válido → isAllowed=true, deniedBy=null", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "estudiante" },
        allowedPermissions: ["projects:read"],
        hasPermission: permFor(["projects:read"]),
      });
      expect(result).toEqual({
        isAllowed: true,
        deniedBy: null,
      } satisfies ProtectedRouteAccessResult);
    });
    it("sin ningún permiso → isAllowed=false, deniedBy='permission'", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "admin" },
        allowedPermissions: ["projects:read", "projects:write"],
        hasPermission: noPermissions,
      });
      expect(result).toEqual({
        isAllowed: false,
        deniedBy: "permission",
      } satisfies ProtectedRouteAccessResult);
    });
    it("permisos mixtos: con uno basta", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "visitor" },
        allowedPermissions: ["a", "b", "c"],
        hasPermission: permFor(["b"]),
      });
      expect(result.isAllowed).toBe(true);
      expect(result.deniedBy).toBeNull();
    });
    it("allowedPermissions con strings vacíos/falsey → se filtran; sin allowedRoles → permitido", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "admin" },
        allowedPermissions: ["", ""],
        hasPermission: noPermissions,
      });
      expect(result.deniedBy).toBeNull();
      expect(result.isAllowed).toBe(true);
    });
    it("allowedPermissions vacíos + allowedRoles definidos → cae a roles", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "visitor" },
        allowedRoles: ["admin"],
        allowedPermissions: [""],
        hasPermission: noPermissions,
      });
      expect(result.deniedBy).toBe("role");
      expect(result.isAllowed).toBe(false);
    });
  });

  describe("rama roles (cuando no hay permisos o solo vacíos)", () => {
    it("rol incluido en allowedRoles → isAllowed=true, deniedBy=null", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "admin" },
        allowedRoles: ["admin", "coordinador"],
        hasPermission: noPermissions,
      });
      expect(result).toEqual({
        isAllowed: true,
        deniedBy: null,
      } satisfies ProtectedRouteAccessResult);
    });
    it("rol no incluido → isAllowed=false, deniedBy='role'", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "estudiante" },
        allowedRoles: ["admin", "coordinador"],
        hasPermission: noPermissions,
      });
      expect(result).toEqual({
        isAllowed: false,
        deniedBy: "role",
      } satisfies ProtectedRouteAccessResult);
    });
    it("allowedRoles vacío → siempre permitido (default true)", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "cualquiera" },
        allowedRoles: [],
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(true);
      expect(result.deniedBy).toBeNull();
    });
    it("allowedRoles undefined → siempre permitido", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "cualquiera" },
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(true);
    });
  });

  describe("normalización de rol (case/space)", () => {
    it("rol mayúsculas vs allowed minúsculas matchea", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "Admin" },
        allowedRoles: ["admin"],
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(true);
    });
    it("allowed con espacios se normaliza", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "admin" },
        allowedRoles: ["  Admin  "],
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(true);
    });
    it("rol vacío/string blanco → no matchea", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "   " },
        allowedRoles: ["admin"],
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(false);
      expect(result.deniedBy).toBe("role");
    });
  });

  describe("user edge cases", () => {
    it("user null → no matchea role → deniedBy='role'", () => {
      const result = evaluateProtectedRouteAccess({
        user: null,
        allowedRoles: ["admin"],
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(false);
      expect(result.deniedBy).toBe("role");
    });
    it("user undefined → idem", () => {
      const result = evaluateProtectedRouteAccess({
        user: undefined,
        allowedRoles: ["admin"],
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(false);
    });
    it("user.role null → idem", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: null },
        allowedRoles: ["admin"],
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(false);
    });
    it("user.role undefined (no deafult) → no matchea", () => {
      const result = evaluateProtectedRouteAccess({
        user: {},
        allowedRoles: ["admin"],
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(false);
    });
  });

  describe("user sin roles pero allowedRoles vacío + sin permisos => permitido", () => {
    it("user null + ningún constraint → isAllowed=true", () => {
      const result = evaluateProtectedRouteAccess({
        user: null,
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(true);
      expect(result.deniedBy).toBeNull();
    });
  });

  describe("permiso tiene prioridad sobre rol (cuando se definen ambos)", () => {
    it("rol cumple pero permiso no → deniedBy='permission' (ahorran roles)", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "admin" },
        allowedRoles: ["admin"],
        allowedPermissions: ["denied:perm"],
        hasPermission: noPermissions,
      });
      expect(result.isAllowed).toBe(false);
      expect(result.deniedBy).toBe("permission");
    });
    it("rol denegado pero permiso cumple → allowed (permission wins)", () => {
      const result = evaluateProtectedRouteAccess({
        user: { role: "visitor" },
        allowedRoles: ["admin"],
        allowedPermissions: ["special:perm"],
        hasPermission: permFor(["special:perm"]),
      });
      expect(result.isAllowed).toBe(true);
      expect(result.deniedBy).toBeNull();
    });
  });
});
