import React from "react";
import { SITE_NAME } from "@/lib/site-config";
import { getCmsPublicPage } from "@/lib/cms/v2";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://ccf.org";
const SITE_KEY = process.env.NEXT_PUBLIC_SITE_KEY || "ccf";

type PublicCmsHeadProps = {
  slug: string;
  fallbackTitle: string;
  fallbackDescription: string;
};

function renderMeta(name: string, content?: string) {
  if (!content) return null;
  return <meta name={name} content={content} />;
}

function renderProperty(prop: string, content?: string) {
  if (!content) return null;
  return <meta property={prop} content={content} />;
}

export default async function PublicCmsHead({
  slug,
  fallbackTitle,
  fallbackDescription,
}: PublicCmsHeadProps) {
  let page: Awaited<ReturnType<typeof getCmsPublicPage>> | null = null;

  try {
    page = await getCmsPublicPage(SITE_KEY, slug, { silent: true });
  } catch {
    page = null;
  }

  const seo = page?.seo_json && typeof page.seo_json === "object" ? page.seo_json : {};
  const title =
    typeof seo.meta_title === "string" && seo.meta_title.trim()
      ? seo.meta_title
      : fallbackTitle;
  const description =
    typeof seo.meta_description === "string" && seo.meta_description.trim()
      ? seo.meta_description
      : fallbackDescription;
  const image =
    typeof seo.meta_image === "string" && seo.meta_image.trim()
      ? seo.meta_image
      : undefined;
  const robotsMeta =
    typeof seo.robots_meta === "string" && seo.robots_meta.trim()
      ? seo.robots_meta
      : undefined;
  const canonical = page?.canonical_url || `${SITE_URL}/${page?.slug || slug}`;
  const jsonLd = page?.json_ld || null;
  const breadcrumbJsonLd = page?.breadcrumb_json_ld || null;

  return (
    <>
      <title>{title}</title>
      {renderMeta("description", description)}
      {renderMeta("author", SITE_NAME)}
      {renderMeta("robots", robotsMeta || "index, follow")}
      {renderProperty("og:title", title)}
      {renderProperty("og:description", description)}
      {renderProperty("og:type", "website")}
      {renderProperty("og:url", canonical)}
      {renderProperty("og:site_name", SITE_NAME)}
      {renderProperty("og:locale", "es_CO")}
      {image ? renderProperty("og:image", image) : null}
      {image ? renderProperty("og:image:alt", title) : null}
      {renderMeta("twitter:card", "summary_large_image")}
      {renderMeta("twitter:title", title)}
      {renderMeta("twitter:description", description)}
      {image ? renderMeta("twitter:image", image) : null}
      <link rel="canonical" href={canonical} />
      {jsonLd ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      ) : null}
      {breadcrumbJsonLd ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }}
        />
      ) : null}
    </>
  );
}
