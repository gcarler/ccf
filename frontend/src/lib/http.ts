import { apiUrl } from "./api";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type QueryValue = string | number | boolean | undefined | null;

export interface ApiFetchOptions {
  method?: HttpMethod;
  body?: unknown;
  token?: string | null;
  headers?: HeadersInit;
  query?: Record<string, QueryValue>;
  cache?: RequestCache;
  credentials?: RequestCredentials;
}

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

function buildUrl(path: string, query?: Record<string, QueryValue>) {
  const target = path.startsWith("http") ? path : apiUrl(path);
  if (!query) return target;
  const url = new URL(target);
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    url.searchParams.set(key, String(value));
  });
  return url.toString();
}

function buildHeaders(base?: HeadersInit) {
  return new Headers({ Accept: "application/json", ...(base || {}) });
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { method = "GET", body, token, headers, query, cache, credentials } = options;
  const url = buildUrl(path, query);
  const finalHeaders = buildHeaders(headers);

  const init: RequestInit = { method, headers: finalHeaders, cache, credentials: credentials ?? "include" };

  // AUTO-INJECT TOKEN FROM LOCALSTORAGE
  let activeToken = token;
  if (!activeToken && typeof window !== 'undefined') {
    activeToken = localStorage.getItem('ccf_token');
  }

  if (activeToken) {
    finalHeaders.set("Authorization", `Bearer ${activeToken}`);
  }

  if (body instanceof FormData) {
    init.body = body;
  } else if (body instanceof URLSearchParams) {
    finalHeaders.set("Content-Type", "application/x-www-form-urlencoded;charset=UTF-8");
    init.body = body;
  } else if (typeof body === "string") {
    if (!finalHeaders.has("Content-Type")) {
      finalHeaders.set("Content-Type", "application/json");
    }
    init.body = body;
  } else if (body !== undefined) {
    finalHeaders.set("Content-Type", "application/json");
    init.body = JSON.stringify(body);
  }

  const nativeFetch: typeof fetch =
    (typeof globalThis !== "undefined" && (globalThis as any).__ccfOriginalFetch) || fetch;
  const response = await nativeFetch(url, init);
  const raw = await response.text();
  const parsed = raw ? safeJsonParse(raw) : undefined;

  if (response.status === 401) {
    // ONLY REDIRECT TO LOGIN IF /auth/me FAILS (CRITICAL AUTH PATH)
    if (typeof window !== 'undefined' && !window.location.pathname.includes('/login') && path.includes('/auth/me')) {
       localStorage.removeItem('ccf_token');
       window.location.href = '/login?expired=true';
    }
    throw new ApiError("Session expired", 401, parsed);
  }

  if (!response.ok) {
    throw new ApiError(response.statusText || "Request failed", response.status, parsed);
  }

  return parsed as T;
}

function safeJsonParse(payload: string) {
  try {
    return JSON.parse(payload);
  } catch {
    return payload;
  }
}
