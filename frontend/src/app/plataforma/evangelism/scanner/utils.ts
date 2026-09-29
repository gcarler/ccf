/**
 * Utilidades para el scanner de credenciales QR y check-in gatekeeper.
 */

/**
 * Extrae y normaliza el token canónico a partir de lecturas directas,
 * URLs completas escaneadas por pistolas físicas 2D o cámaras web,
 * tokens codificados en URI y prefijos canónicos CCF-EVT- y CCF-PER-.
 */
export function sanitizeAndExtractQrToken(rawInput: string): string {
  if (!rawInput) return '';
  let cleaned = rawInput.trim();
  if (!cleaned) return '';

  // Decodificar URI components por si viene URL-encoded (ej: %20, %3D, etc.)
  try {
    if (cleaned.includes('%')) {
      cleaned = decodeURIComponent(cleaned);
    }
  } catch {
    // Si la decodificación falla, mantener cleaned tal cual
  }

  // 1. Si contiene 'token=', extraer mediante URLSearchParams o Regex
  if (cleaned.includes('token=')) {
    try {
      if (cleaned.startsWith('http://') || cleaned.startsWith('https://') || cleaned.includes('?')) {
        const fullUrl = cleaned.startsWith('http')
          ? cleaned
          : `https://dummy.local/${cleaned.startsWith('?') ? '' : '?'}${cleaned}`;
        const parsed = new URL(fullUrl);
        const tokenVal = parsed.searchParams.get('token');
        if (tokenVal) {
          return tokenVal.trim();
        }
      }
    } catch {
      // Fallback a regex
    }

    const match = cleaned.match(/[?&]token=([^&#\s]+)/) || cleaned.match(/\btoken=([^&#\s]+)/);
    if (match && match[1]) {
      try {
        return decodeURIComponent(match[1]).trim();
      } catch {
        return match[1].trim();
      }
    }
  }

  // 2. Extraer prefijo canónico CCF-EVT- si viene embebido en alguna ruta o texto
  const evtMatch = cleaned.match(/(CCF-EVT-[A-Za-z0-9_\-]+)/);
  if (evtMatch && evtMatch[1]) {
    return evtMatch[1].trim();
  }

  // 3. Extraer prefijo canónico CCF-PER- si viene embebido en alguna ruta o texto
  const perMatch = cleaned.match(/(CCF-PER-[A-Za-z0-9_\-]+)/);
  if (perMatch && perMatch[1]) {
    return perMatch[1].trim();
  }

  return cleaned;
}
