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
  timeout?: number;
  silent?: boolean;
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

  // For relative paths in the browser, we need an absolute base for URL()
  const base = target.startsWith("http")
    ? undefined
    : typeof window !== "undefined"
    ? window.location.origin
    : "http://localhost:3000";

  const url = base ? new URL(target, base) : new URL(target);
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
  const { method = "GET", body, token, headers, query, cache, credentials, timeout, silent } = options;
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

  // AbortController: longer timeout on server (SSR cold start) vs client
  const isServer = typeof window === 'undefined';
  const defaultTimeoutMs = isServer ? 30_000 : 15_000;
  const timeoutMs = timeout || defaultTimeoutMs;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const nativeFetch: typeof fetch =
    (typeof globalThis !== "undefined" && (globalThis as any).__ccfOriginalFetch) || fetch;

  let response: Response;
  try {
    response = await nativeFetch(url, { ...init, signal: controller.signal });
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      // Silently treat timeouts as a network error â€” not a crash
      throw new ApiError('Request timed out', 0, err);
    }
    console.error(`[API_NETWORK_ERROR] ${method} ${path}:`, err.message);
    throw new ApiError(err.message || 'Network error', 0, err);
  } finally {
    clearTimeout(timeoutId);
  }

  const raw = await response.text();
  const parsed = raw ? safeJsonParse(raw) : undefined;

  if (response.status === 401) {
    console.warn(`[API_UNAUTHORIZED] ${path}`);
    const isLoginPath = path.includes('/auth/login') || (typeof window !== 'undefined' && window.location.pathname.includes('/login'));
    if (typeof window !== 'undefined' && !isLoginPath) {
       localStorage.removeItem('ccf_token');
       window.location.href = '/login?expired=true';
    }
    const defaultMsg = isLoginPath ? "Credenciales incorrectas" : "Session expired";
    throw new ApiError(parsed?.detail || parsed?.message || defaultMsg, 401, parsed);
  }

  if (!response.ok) {
    if (!silent) console.error(`[API_FAILURE] ${response.status} ${method} ${path}:`, parsed);
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

