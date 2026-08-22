/**
 * Filtro reutilizable de búsqueda de personas para cualquier módulo de la
 * plataforma. Normaliza acentos/case/espacios y casa por prefijo del nombre
 * completo o por subsecuencia de palabras (nombres compuestos incluidos).
 */

/**
 * Cache acotado de normalización: los nombres/roles/emails de las listas son
 * estables en una sesión, así que normalizar una y otra vez en cada tecla es
 * desperdicio. Función pura → el cache por string de entrada es seguro.
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
    CACHE_NORMALIZACION.clear();
  }
  CACHE_NORMALIZACION.set(key, normalized);
  return normalized;
}

/**
 * Indica si la persona (nombre completo) coincide con el query de búsqueda.
 *
 * - Query vacío → true (sin filtro).
 * - Una palabra → prefijo de cualquier palabra del nombre: "meza" casa con
 *   "Luis Ricardo Meza" (búsqueda por apellido) y "luis" con "Ana Luis Meza".
 * - Varias palabras → cada una debe ser prefijo de alguna palabra del nombre,
 *   en orden ("juan meza" casa con "Juan Luis Meza"; "l m" con "Luis Ricardo Meza").
 */
export function filtroAPersonas(name: string | null | undefined, query: string): boolean {
  const normalizedName = normalizarBusquedaPersona(name);
  const normalizedQuery = normalizarBusquedaPersona(query);
  if (!normalizedQuery) return true;
  if (normalizedName.startsWith(normalizedQuery)) return true;

  const nameWords = normalizedName.split(' ');
  const queryWords = normalizedQuery.split(' ');
  // Una sola palabra: prefijo de CUALQUIER palabra del nombre (nombre o
  // apellido): "meza" encuentra "Luis Ricardo Meza".
  if (queryWords.length === 1) {
    return nameWords.some((word) => word.startsWith(queryWords[0]));
  }

  // Multi-palabra: cada palabra del query debe ser prefijo de alguna palabra
  // del nombre, en orden (subsecuencia). Así "juan meza" encuentra a
  // "Juan Luis Meza" (nombres compuestos) y "l m" a "Luis Ricardo Meza".
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

/**
 * Forma mínima de una persona para búsqueda multi-campo. Acepta por
 * compatibilidad estructural cualquier tipo de persona de la plataforma
 * (evangelismo, CRM, etc.) con estos campos opcionales.
 */
export interface PersonaBusqueda {
  id?: string | null;
  // Username de la cuenta de plataforma (auth_users). Se busca con "@".
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
 * Búsqueda sobre una persona completa:
 *
 * - Query que empieza con "@" → busca por USUARIO (username de la cuenta,
 *   estilo mensajería): "@gscarlosernesto" encuentra esa cuenta.
 * - Sin "@" → multi-campo: nombre (con `filtroAPersonas`), email, teléfonos,
 *   documento y rol (coincidencia parcial).
 *
 * Query vacío → true; persona vacía → false.
 *
 * Reemplaza el patrón repetido en cada pantalla de:
 * `filtroAPersonas(p.nombre_completo, q) || normalizar(p.email).includes(q) || ...`
 */
export function filtroAPersona(persona: PersonaBusqueda | null | undefined, query: string): boolean {
  const rawQuery = (query ?? '').trim();
  if (!rawQuery) return true;
  if (!persona) return false;

  // Un '@' inicial significa búsqueda por USUARIO (username de la cuenta),
  // estilo mensajería: "@gscarlosernesto" busca ese username. Los nombres se
  // buscan SIN '@'.
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
    if (campo && normalizarBusquedaPersona(campo).includes(normalizedQuery)) return true;
  }

  for (const rol of [persona.church_role, persona.church_role_effective]) {
    if (rol && normalizarBusquedaPersona(rol).includes(normalizedQuery)) return true;
  }
  return false;
}
