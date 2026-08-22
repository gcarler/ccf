/** Shared, deterministic person-name search rules for platform selectors. */
export function normalizePersonSearch(value: string | null | undefined): string {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Matches the beginning of the full name, including multi-word prefixes. */
export function matchesPersonNamePrefix(name: string | null | undefined, query: string): boolean {
  const normalizedName = normalizePersonSearch(name);
  const normalizedQuery = normalizePersonSearch(query);
  if (!normalizedQuery) return true;
  if (normalizedName.startsWith(normalizedQuery)) return true;

  const nameWords = normalizedName.split(' ');
  const queryWords = normalizedQuery.split(' ');
  return queryWords.length > 1 && queryWords.every((word, index) => nameWords[index]?.startsWith(word));
}
