const DEFAULT_API_URL = "/api";

const isServer = typeof window === 'undefined';

const SERVER_API_URL = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
const CLIENT_API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || DEFAULT_API_URL;

export const API_BASE_URL = isServer ? SERVER_API_URL : CLIENT_API_URL;

export function apiUrl(path: string): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const base = API_BASE_URL.replace(/\/$/, "");
  if (base.endsWith("/api") && cleanPath.startsWith("/api/")) {
    return `${base.slice(0, -4)}${cleanPath}`;
  }
  return `${base}${cleanPath}`;
}

