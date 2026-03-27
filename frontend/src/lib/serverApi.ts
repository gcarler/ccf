import { cookies } from 'next/headers';
import { apiUrl } from './api';

async function parseResponse(response: Response) {
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function serverApiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const cookieStore = cookies();
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  cookieStore.getAll().forEach((cookie) => {
    headers.append('cookie', `${cookie.name}=${cookie.value}`);
  });
  const response = await fetch(apiUrl(path), {
    ...init,
    headers,
    cache: init.cache ?? 'no-store',
  });

  const body = await parseResponse(response);
  if (!response.ok) {
    const error = new Error('Server API request failed');
    (error as any).detail = body;
    throw error;
  }
  return body as T;
}
