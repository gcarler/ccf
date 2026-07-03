// Central site identity — configure per deployment via env vars.
// Each church sets NEXT_PUBLIC_SITE_KEY, NEXT_PUBLIC_SITE_NAME, etc. in their .env.local
export const SITE_KEY   = process.env.NEXT_PUBLIC_SITE_KEY   ?? "ccf";
export const SITE_NAME  = process.env.NEXT_PUBLIC_SITE_NAME  ?? "Mi Comunidad";
export const SITE_URL   = process.env.NEXT_PUBLIC_SITE_URL   ?? "";
export const SITE_EMAIL = process.env.NEXT_PUBLIC_SITE_EMAIL ?? "";
