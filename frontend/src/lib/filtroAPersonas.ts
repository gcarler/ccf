/**
 * Filtro reutilizable de búsqueda de personas para cualquier módulo de la
 * plataforma. Normaliza acentos/case/espacios y casa por prefijo del nombre
 * completo o por subsecuencia de palabras (nombres compuestos incluidos).
 */

const CACHE_NORMALIZACION = new Map<string, string>();
const CACHE_MAX_ENTRIES = 5000;

/** Normaliza un texto para comparación: minúsculas, sin acentos, espacios simples. */
export function normalizarBusquedaPersona(value: string | null | undefined): string {
  const key = value ?? '';
  const cached = CACHE_NORMALIZACION.get(key);
  if (cached !== undefined) return cached;
  const normalized = String(key)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es')
    .replace(/\s+/g, ' ')
    .trim();
  if (CACHE_NORMALIZACION.size >= CACHE_MAX_ENTRIES) {
    const oldestKey = CACHE_NORMALIZACION.keys().next().value;
    if (oldestKey !== undefined) CACHE_NORMALIZACION.delete(oldestKey);
  }
  CACHE_NORMALIZACION.set(key, normalized);
  return normalized;
}

/**
 * Indica si un nombre coincide con el query. Una palabra es prefijo de
 * cualquier palabra del nombre; varias palabras deben aparecer como
 * prefijos en orden.
 */
export function filtroAPersonas(name: string | null | undefined, query: string): boolean {
  const normalizedName = normalizarBusquedaPersona(name);
  const normalizedQuery = normalizarBusquedaPersona(query);
  if (!normalizedQuery) return true;
  if (normalizedName.startsWith(normalizedQuery)) return true;

  const nameWords = normalizedName.split(' ');
  const queryWords = normalizedQuery.split(' ');
  if (queryWords.length === 1) return nameWords.some((word) => word.startsWith(queryWords[0]));

  let nameIndex = 0;
  for (const queryWord of queryWords) {
    let matched = false;
    while (nameIndex < nameWords.length) {
      if (nameWords[nameIndex].startsWith(queryWord)) {
        matched = true;
        nameIndex += 1;
        break;
      }
      nameIndex += 1;
    }
    if (!matched) return false;
  }
  return true;
}

/** Forma mínima de una persona para búsqueda. */
export interface PersonaBusqueda {
  id?: string | null;
  username?: string | null;
  nombre_completo?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  phone?: string | null;
  telefono?: string | null;
  mobile_phone?: string | null;
  landline_phone?: string | null;
  other_phone?: string | null;
  id_number?: string | null;
  document_number?: string | null;
  church_role?: string | null;
  church_role_effective?: string | null;
}

/**
 * Búsqueda estricta para listados: sin @ busca únicamente nombre/apellido;
 * con @ busca el username de la cuenta.
 */
export function filtroAPersona(persona: PersonaBusqueda | null | undefined, query: string): boolean {
  const rawQuery = (query ?? '').trim();
  if (!rawQuery) return true;
  if (!persona) return false;

  if (rawQuery.startsWith('@')) {
    const normalizedUsernameQuery = normalizarBusquedaPersona(rawQuery.slice(1));
    if (!normalizedUsernameQuery) return false;
    return persona.username ? normalizarBusquedaPersona(persona.username).startsWith(normalizedUsernameQuery) : false;
  }

  const nombre =
    persona.nombre_completo ||
    [persona.first_name, persona.last_name].filter(Boolean).join(' ').trim() ||
    '';
  return filtroAPersonas(nombre, normalizarBusquedaPersona(rawQuery));
}

/** Búsqueda explícita por nombre, correo, teléfono, documento o cargo. */
export function filtroAPersonaMultiCampo(persona: PersonaBusqueda | null | undefined, query: string): boolean {
  const rawQuery = (query ?? '').trim();
  if (!rawQuery) return true;
  if (!persona) return false;
  if (rawQuery.startsWith('@')) {
    const normalizedUsernameQuery = normalizarBusquedaPersona(rawQuery.slice(1));
    if (!normalizedUsernameQuery) return false;
    return persona.username ? normalizarBusquedaPersona(persona.username).startsWith(normalizedUsernameQuery) : false;
  }

  const normalizedQuery = normalizarBusquedaPersona(rawQuery);
  const nombre =
    persona.nombre_completo ||
    [persona.first_name, persona.last_name].filter(Boolean).join(' ').trim() ||
    '';
  if (filtroAPersonas(nombre, normalizedQuery)) return true;

  const identificadores = [
    persona.email,
    persona.phone,
    persona.telefono,
    persona.mobile_phone,
    persona.landline_phone,
    persona.other_phone,
    persona.id_number,
    persona.document_number,
  ];
  for (const campo of identificadores) {
    if (!campo) continue;
    const normalizedCampo = normalizarBusquedaPersona(campo);
    if (normalizedCampo.includes(normalizedQuery)) return true;
    const compactCampo = normalizedCampo.replace(/[^\d+]/g, '');
    const compactQuery = normalizedQuery.replace(/[^\d+]/g, '');
    if (compactQuery && compactCampo.includes(compactQuery)) return true;
  }

  for (const rol of [persona.church_role, persona.church_role_effective]) {
    if (rol && normalizarBusquedaPersona(rol).includes(normalizedQuery)) return true;
  }
  return false;
}
