import { NextResponse } from "next/server";
import { serverApiFetch } from "@/lib/serverApi";
import { SITE_KEY, SITE_URL } from "@/lib/site-config";

const PUBLIC_SITE_URL = SITE_URL.replace(/\/$/, "");

interface SitemapEntry {
  loc: string;
  lastmod?: string;
  changefreq?: string;
  priority?: number;
}

interface PublishedPageSummary {
  slug?: string;
  status?: string;
  updated_at?: string | null;
}

async function fetchPublishedPages(): Promise<SitemapEntry[]> {
  try {
    const data = await serverApiFetch<{ items?: PublishedPageSummary[] }>(
      `/cms/v2/public/sites/${SITE_KEY}/pages?limit=500`,
      { cache: "no-store" },
    );
    const items = Array.isArray(data?.items) ? data.items : [];
    return items
      .filter((page) => page.status === "published" && page.slug && page.slug !== "footer")
      .map((page) => ({
        loc: page.slug === "home" ? `${PUBLIC_SITE_URL}/` : `${PUBLIC_SITE_URL}/${page.slug}`,
        lastmod: page.updated_at ? new Date(page.updated_at).toISOString() : undefined,
        changefreq: "weekly",
        priority: page.slug === "home" ? 1.0 : 0.7,
      }));
  } catch {
    return [];
  }
}

const STATIC_ROUTES: SitemapEntry[] = [
  { loc: `${PUBLIC_SITE_URL}/`, changefreq: "daily", priority: 1.0 },
  { loc: `${PUBLIC_SITE_URL}/nosotros`, changefreq: "monthly", priority: 0.8 },
  { loc: `${PUBLIC_SITE_URL}/pastores`, changefreq: "monthly", priority: 0.8 },
  { loc: `${PUBLIC_SITE_URL}/conocer-a-jesus`, changefreq: "monthly", priority: 0.9 },
  { loc: `${PUBLIC_SITE_URL}/eventos`, changefreq: "weekly", priority: 0.8 },
  { loc: `${PUBLIC_SITE_URL}/predicas`, changefreq: "weekly", priority: 0.8 },
  { loc: `${PUBLIC_SITE_URL}/cursos`, changefreq: "weekly", priority: 0.7 },
  { loc: `${PUBLIC_SITE_URL}/sedes`, changefreq: "monthly", priority: 0.7 },
  { loc: `${PUBLIC_SITE_URL}/boletin`, changefreq: "weekly", priority: 0.7 },
  { loc: `${PUBLIC_SITE_URL}/testimonios`, changefreq: "weekly", priority: 0.8 },
  { loc: `${PUBLIC_SITE_URL}/privacy`, changefreq: "yearly", priority: 0.3 },
];

function deduplicateEntries(entries: SitemapEntry[]): SitemapEntry[] {
  return Array.from(new Map(entries.map((entry) => [entry.loc, entry])).values());
}

/*
 * The CMS page list is authoritative for published routes. Static routes are
 * retained for dedicated renderers, while duplicate CMS entries are removed.
 */
function buildEntries(cmsPages: SitemapEntry[]): SitemapEntry[] {
  return deduplicateEntries([...STATIC_ROUTES, ...cmsPages]);
}

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
  const allEntries = buildEntries(cmsPages);
  const xml = buildSitemapXml(allEntries);

  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
    },
  });
}
