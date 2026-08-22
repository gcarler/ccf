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
 * - Una palabra → prefijo del nombre completo ("luis" casa con "Luis Ricardo").
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
  // Una sola palabra: solo casa con el prefijo del nombre completo (contrato
  // documentado: "ana luis" no se encuentra buscando "luis").
  if (queryWords.length < 2) return false;

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
