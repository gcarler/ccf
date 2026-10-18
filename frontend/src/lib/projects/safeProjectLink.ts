/** Returns a navigable project link, blocking executable and ambiguous schemes. */
export function getSafeProjectLink(value?: string | null): string | null {
  const normalized = value?.trim();
  if (!normalized || /[\\\u0000-\u001f\u007f]/.test(normalized) || normalized.startsWith('//')) {
    return null;
  }

  try {
    const parsed = new URL(normalized, 'https://ccf.invalid');
    if (parsed.origin === 'https://ccf.invalid') return normalized;
    if (!['http:', 'https:'].includes(parsed.protocol) || !parsed.hostname) return null;
    if (parsed.username || parsed.password) return null;
    return normalized;
  } catch {
    return null;
  }
}

/**
 * PMI — Guarda de enlaces internos de plataforma: true sólo cuando el enlace
 * seguro es una ruta interna de proyectos ('/plataforma/projects') o un
 * artefacto estático del módulo ('/api/static/projects'). Enlaces externos,
 * directos a otras rutas o no seguros devuelven false.
 */
export function isInternalPlatformProjectLink(value?: string | null): boolean {
  const safe = getSafeProjectLink(value);
  if (!safe) return false;
  return safe.startsWith('/plataforma/projects') || safe.startsWith('/api/static/projects');
}
