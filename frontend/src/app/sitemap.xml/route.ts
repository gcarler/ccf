import { NextResponse } from "next/server";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://ccfministerio.com";

interface SitemapEntry {
  loc: string;
  lastmod?: string;
  changefreq?: string;
  priority?: number;
}

async function fetchPublishedPages(): Promise<SitemapEntry[]> {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/cms/v2/public/sites/default/pages`, {
      headers: { Accept: "application/json" },
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    const items = Array.isArray(data) ? data : data?.items || [];
    return items
      .filter((p: any) => p.status === "published" && p.slug)
      .map((p: any) => ({
        loc: `${SITE_URL}/${p.slug}`,
        lastmod: p.updated_at ? new Date(p.updated_at).toISOString() : undefined,
        changefreq: "weekly",
        priority: p.slug === "home" || p.slug === "" ? 1.0 : 0.7,
      }));
  } catch {
    return [];
  }
}

const STATIC_ROUTES: SitemapEntry[] = [
  { loc: `${SITE_URL}/`, changefreq: "daily", priority: 1.0 },
  { loc: `${SITE_URL}/nosotros`, changefreq: "monthly", priority: 0.8 },
  { loc: `${SITE_URL}/pastores`, changefreq: "monthly", priority: 0.8 },
  { loc: `${SITE_URL}/conocer-a-jesus`, changefreq: "monthly", priority: 0.9 },
  { loc: `${SITE_URL}/eventos`, changefreq: "weekly", priority: 0.8 },
  { loc: `${SITE_URL}/predicas`, changefreq: "weekly", priority: 0.8 },
  { loc: `${SITE_URL}/cursos`, changefreq: "weekly", priority: 0.7 },
  { loc: `${SITE_URL}/sedes`, changefreq: "monthly", priority: 0.7 },
  { loc: `${SITE_URL}/boletin`, changefreq: "weekly", priority: 0.7 },
  { loc: `${SITE_URL}/testimonios`, changefreq: "weekly", priority: 0.8 },
  { loc: `${SITE_URL}/privacidad`, changefreq: "yearly", priority: 0.3 },
];

function buildSitemapXml(entries: SitemapEntry[]): string {
  const urlEntries = entries
    .map((e) => {
      const lastmod = e.lastmod ? `<lastmod>${e.lastmod}</lastmod>` : "";
      const changefreq = e.changefreq ? `<changefreq>${e.changefreq}</changefreq>` : "";
      const priority = e.priority !== undefined ? `<priority>${e.priority.toFixed(1)}</priority>` : "";
      return `  <url>\n    <loc>${escapeXml(e.loc)}</loc>\n    ${lastmod}\n    ${changefreq}\n    ${priority}\n  </url>`;
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urlEntries}\n</urlset>`;
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export async function GET() {
  const cmsPages = await fetchPublishedPages();
  const allEntries = [...STATIC_ROUTES, ...cmsPages];
  const xml = buildSitemapXml(allEntries);

  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
    },
  });
}
