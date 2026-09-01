/** Canonical public routes consumed by the public renderers.
 * Keep this map explicit: the CMS slug is an implementation key, while the
 * public path is what editors and visitors recognize.
 */
const CMS_TO_PUBLIC_ROUTE: Record<string, string> = {
  home: "/",
  about: "/nosotros",
  locations: "/sedes",
  sermons: "/predicas",
  courses: "/cursos",
  newsletter: "/boletin",
  testimonials: "/testimonios",
  pastors: "/pastores",
  blog: "/blog",
  events: "/eventos",
  donate: "/donate",
  books: "/books",
  privacy: "/privacy",
  terms: "/terms",
  aniversario40: "/aniversario40",
  discover: "/conocer-a-jesus",
};

export function publicRouteForCmsSlug(slug: string): string | null {
  return CMS_TO_PUBLIC_ROUTE[slug.trim().toLowerCase()] ?? null;
}
