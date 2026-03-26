import { API_BASE_URL } from './api';

const fallbackRandom = () =>
  (typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? (crypto.randomUUID as () => string)()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`);

export function buildWsUrl(path: string) {
  const normalizedBase = API_BASE_URL.replace(/^http/i, (protocol) =>
    protocol.toLowerCase() === 'https' ? 'wss' : 'ws'
  );
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${normalizedBase}${cleanPath}`;
}

export function resolveClientId(clientId?: string) {
  if (clientId) return clientId;
  return `anon-${fallbackRandom()}`;
}
