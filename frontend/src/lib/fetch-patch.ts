import { API_BASE_URL } from "./api";
import { apiFetch, ApiError, ApiFetchOptions } from "./http";

declare global {
  // eslint-disable-next-line no-var
  var __ccfFetchPatched: boolean | undefined;
  // eslint-disable-next-line no-var
  var __ccfOriginalFetch: typeof fetch | undefined;
}

type RequestLike = Request | URL | string;

const globalScope: any = typeof globalThis !== "undefined" ? globalThis : global;

if (!globalScope.__ccfFetchPatched && typeof globalScope.fetch === "function") {
  const originalFetch = globalScope.fetch.bind(globalScope);
  globalScope.__ccfOriginalFetch = originalFetch;
  globalScope.__ccfFetchPatched = true;

  globalScope.fetch = async (input: RequestLike, init?: RequestInit) => {
    const targetUrl = resolveUrl(input);
    if (targetUrl && targetUrl.startsWith(API_BASE_URL)) {
      return handleApiFetch(targetUrl, init);
    }
    return originalFetch(input as RequestInfo, init);
  };
}

function resolveUrl(input: RequestLike): string | null {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  if (typeof Request !== "undefined" && input instanceof Request) {
    return input.url;
  }
  return null;
}

async function handleApiFetch(url: string, init?: RequestInit) {
  const path = url.replace(API_BASE_URL, "") || "/";
  const headers = new Headers(init?.headers);
  const token = extractToken(headers);
  const options: ApiFetchOptions = {
    method: (init?.method as ApiFetchOptions["method"]) || undefined,
    headers: headers,
    cache: init?.cache,
    token,
  };

  if (init?.body !== undefined) {
    options.body = init.body as BodyInit;
  }

  try {
    const data = await apiFetch(path, options);
    return buildResponse(data, 200);
  } catch (error) {
    if (error instanceof ApiError) {
      return buildResponse(error.detail ?? {}, error.status || 500);
    }
    throw error;
  }
}

function extractToken(headers: Headers) {
  const auth = headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) {
    headers.delete("Authorization");
    return auth.slice(7);
  }
  return undefined;
}

function buildResponse(body: unknown, status: number) {
  const payload = body === undefined ? "null" : JSON.stringify(body);
  return new Response(payload, {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
