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
  signal?: AbortSignal;
}

// Deduplicate concurrent refresh calls — all callers share the same promise.
let _refreshPromise: Promise<string | null> | null = null;

async function _refreshSession(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    if (typeof window === "undefined") return null;
    const refreshToken = sessionStorage.getItem("ccf_refresh_token");
    if (!refreshToken) return null;

    try {
      const nativeFetch: typeof fetch =
        (typeof globalThis !== "undefined" && (globalThis as any).__ccfOriginalFetch) || fetch;
      
      const res = await nativeFetch(apiUrl("/v3/auth/refresh"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return null;
      const data = await res.json();
      if (data.access_token) {
        sessionStorage.setItem("ccf_token", data.access_token);
        if (data.refresh_token) sessionStorage.setItem("ccf_refresh_token", data.refresh_token);
        return data.access_token as string;
      }
      return null;
    } catch {
      return null;
    }
  })().finally(() => {
    _refreshPromise = null;
  });

  return _refreshPromise;
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

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}, _isRetry = false): Promise<T> {
  const { method = "GET", body, token, headers, query, cache, credentials, timeout, silent } = options;
  const url = buildUrl(path, query);
  const finalHeaders = buildHeaders(headers);

  const init: RequestInit = { method, headers: finalHeaders, cache, credentials: credentials ?? "include" };

  // AUTO-INJECT TOKEN FROM SESSIONSTORAGE
  let activeToken = token;
  if (!activeToken && typeof window !== 'undefined') {
    activeToken = sessionStorage.getItem('ccf_token');
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

  // Link external signal (e.g., from component unmount) with internal timeout controller
  let cleanupExternalSignal: (() => void) | undefined;
  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      const onAbort = () => controller.abort();
      options.signal.addEventListener('abort', onAbort);
      cleanupExternalSignal = () => options.signal?.removeEventListener('abort', onAbort);
    }
  }

  const nativeFetch: typeof fetch =
    (typeof globalThis !== "undefined" && (globalThis as any).__ccfOriginalFetch) || fetch;

  let response: Response;
  try {
    response = await nativeFetch(url, { ...init, signal: controller.signal });
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      // Silently treat timeouts as a network error, not a crash.
      throw new ApiError('Request timed out', 0, err);
    }
    if (!silent) {
      console.error(`[API_NETWORK_ERROR] ${method} ${path}:`, err.message);
    }
    throw new ApiError(err.message || 'Network error', 0, err);
  } finally {
    clearTimeout(timeoutId);
    cleanupExternalSignal?.();
  }

  const raw = await response.text();
  const parsed = raw ? safeJsonParse(raw) : undefined;

  if (response.status === 401) {
    const isAuthPath =
      path.includes("/v3/auth/login") ||
      path.includes("/v3/auth/refresh") ||
      path.includes("/v3/auth/logout");

    // Auto-refresh: if this is not an auth endpoint and not already a retry, try to renew the session.
    if (!isAuthPath && !_isRetry && typeof window !== "undefined") {
      const newToken = await _refreshSession();
      if (newToken) {
        return apiFetch<T>(path, { ...options, token: newToken }, true);
      }
      // Refresh failed — session is truly expired.
      sessionStorage.removeItem("ccf_token");
      sessionStorage.removeItem("ccf_refresh_token");
      window.location.href = "/login?expired=true";
    }

    const defaultMsg = isAuthPath ? "Credenciales incorrectas" : "Sesión expirada";
    throw new ApiError(parsed?.detail || parsed?.message || defaultMsg, 401, parsed);
  }

  if (!response.ok) {
    if (!silent) console.error(`[API_FAILURE] ${response.status} ${method} ${path}:`, parsed);
    throw new ApiError(response.statusText || "Request failed", response.status, parsed);
  }

  return parsed as T;
}

export async function apiFetchBlob(path: string, options: ApiFetchOptions = {}): Promise<Blob> {
  const { method = "GET", token, headers, query, cache, credentials } = options;
  const url = buildUrl(path, query);
  const finalHeaders = buildHeaders(headers);

  let activeToken = token;
  if (!activeToken && typeof window !== "undefined") {
    activeToken = sessionStorage.getItem("ccf_token");
  }

  if (activeToken) {
    finalHeaders.set("Authorization", `Bearer ${activeToken}`);
  }

  const nativeFetch: typeof fetch =
    (typeof globalThis !== "undefined" && (globalThis as any).__ccfOriginalFetch) || fetch;
  const response = await nativeFetch(url, {
    method,
    headers: finalHeaders,
    cache,
    credentials: credentials ?? "include",
  });

  if (!response.ok) {
    const raw = await response.text();
    const parsed = raw ? safeJsonParse(raw) : undefined;
    throw new ApiError(response.statusText || "Request failed", response.status, parsed);
  }

  return response.blob();
}

function safeJsonParse(payload: string) {
  try {
    return JSON.parse(payload);
  } catch {
    return payload;
  }
}

export function extractErrorMessage(err: unknown, fallback = "Error inesperado"): string {
  if (err instanceof ApiError) {
    if (typeof err.detail === "object" && err.detail !== null) {
      const detail = err.detail as Record<string, unknown>;
      if (typeof detail.detail === "string") return detail.detail;
      if (typeof detail.message === "string") return detail.message;
    }
    if (typeof err.detail === "string") return err.detail;
    return err.message || fallback;
  }
  if (err instanceof Error) return err.message || fallback;
  return fallback;
}
