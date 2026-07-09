import React from "react";
import { notFound } from "next/navigation";
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";
import BreadcrumbNav from "@/components/public/cms/BreadcrumbNav";
import { Metadata } from "next";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { SITE_KEY } from "@/lib/site-config";
import { CmsPublicPage } from "@/types/cms-v2";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://ccf.org";

export async function generateMetadata({ params }: { params: Promise<{ slug: string[] }> }): Promise<Metadata> {
  const resolvedParams = await params;
  const slugValue = Array.isArray(resolvedParams?.slug) ? resolvedParams.slug.join("/") : "";
  if (!slugValue) return {};

  try {
    const page = await getCmsPublicPage(SITE_KEY, slugValue);
    if (!page) return {};
    const seo = page.seo_json || {};
    const metaTitle = typeof seo.meta_title === "string" && seo.meta_title.trim() ? seo.meta_title : page.title;
    const metaDescription = typeof seo.meta_description === "string" && seo.meta_description.trim() ? seo.meta_description : undefined;
    const metaImage = typeof seo.meta_image === "string" && seo.meta_image.trim() ? seo.meta_image : undefined;
    const canonical = page.canonical_url || `${SITE_URL}/${page.slug}`;
    const robotsMeta = typeof seo.robots_meta === "string" && seo.robots_meta.trim() ? seo.robots_meta : undefined;

    return {
      title: metaTitle,
      description: metaDescription,
      alternates: {
        canonical,
      },
      robots: robotsMeta || "index, follow",
      ...(robotsMeta
        ? {}
        : {
            openGraph: {
              title: metaTitle,
              description: metaDescription,
              url: canonical,
              images: metaImage ? [metaImage] : undefined,
              type: "website",
              locale: "es_CO",
              siteName: "CCF",
            },
            twitter: {
              card: "summary_large_image",
              title: metaTitle,
              description: metaDescription,
              images: metaImage ? [metaImage] : undefined,
            },
          }),
    };
  } catch {
    return {};
  }
}

export default async function CcfDynamicPage({ params }: { params: Promise<{ slug: string[] }> }) {
  const resolvedParams = await params;
  const slugValue = Array.isArray(resolvedParams?.slug) ? resolvedParams.slug.join("/") : "";

  if (!slugValue) {
    notFound();
  }

  let page: CmsPublicPage | null = null;
  try {
    page = await getCmsPublicPage(SITE_KEY, slugValue);
  } catch {
    notFound();
  }

  if (!page) {
    notFound();
  }

  const jsonLdScripts: string[] = [];
  if (page.json_ld) {
    jsonLdScripts.push(`<script type="application/ld+json">${JSON.stringify(page.json_ld)}</script>`);
  }
  if (page.breadcrumb_json_ld) {
    jsonLdScripts.push(`<script type="application/ld+json">${JSON.stringify(page.breadcrumb_json_ld)}</script>`);
  }

  return (
    <>
      {jsonLdScripts.length > 0 && (
        <head dangerouslySetInnerHTML={{ __html: jsonLdScripts.join("") }} />
      )}
      <main className="flex-1 px-3 md:px-6 lg:px-8 xl:px-12 pt-[100px] pb-16 space-y-8">
        {page.breadcrumbs && page.breadcrumbs.length > 1 && (
          <div className="max-w-7xl mx-auto w-full">
            <BreadcrumbNav items={page.breadcrumbs} />
          </div>
        )}
        {page.sections.filter((section) => section.is_visible).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)).map((section) => (
          <PublicSectionRenderer key={section.id} section={section} />
        ))}
      </main>
    </>
  );
}
