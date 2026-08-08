import { describe, it, expect } from "vitest";

import { SITE_KEY, SITE_NAME, SITE_URL, SITE_EMAIL } from "./site-config";

describe("site-config", () => {
  it("exporta las 4 constantes con defaults conocidos", () => {
    expect(typeof SITE_KEY).toBe("string");
    expect(SITE_KEY.length).toBeGreaterThan(0);
    expect(typeof SITE_NAME).toBe("string");
    expect(SITE_NAME.length).toBeGreaterThan(0);
    expect(typeof SITE_URL).toBe("string");
    expect(typeof SITE_EMAIL).toBe("string");
  });
  it("respeto los defaults cuando no hay env", () => {
    // valores por defecto — los assert si no hay env vars; si los hay,
    // simplemente validamos tipo.
    if (!process.env.NEXT_PUBLIC_SITE_KEY) expect(SITE_KEY).toBe("ccf");
    if (!process.env.NEXT_PUBLIC_SITE_NAME) expect(SITE_NAME).toBe("Mi Comunidad");
    if (!process.env.NEXT_PUBLIC_SITE_URL) expect(SITE_URL).toBe("");
    if (!process.env.NEXT_PUBLIC_SITE_EMAIL) expect(SITE_EMAIL).toBe("");
  });
});
