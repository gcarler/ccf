import React from "react";
import { notFound } from "next/navigation";
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";
import { Metadata } from "next";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { CmsPublicPage } from "@/types/cms-v2";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://faro.ccf.org";

export async function generateMetadata({ params }: { params: Promise<{ slug: string[] }> }): Promise<Metadata> {
  const resolvedParams = await params;
  const slugValue = Array.isArray(resolvedParams?.slug) ? resolvedParams.slug.join("/") : "";
  if (!slugValue) return {};

  try {
    const page = await getCmsPublicPage("default", slugValue);
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
      robots: robotsMeta
        ? undefined
        : {
            index: true,
            follow: true,
          },
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
              siteName: "FARO",
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

export default async function FaroDynamicPage({ params }: { params: Promise<{ slug: string[] }> }) {
  const resolvedParams = await params;
  const slugValue = Array.isArray(resolvedParams?.slug) ? resolvedParams.slug.join("/") : "";

  if (!slugValue) {
    notFound();
  }

  let page: CmsPublicPage | null = null;
  try {
    page = await getCmsPublicPage("default", slugValue);
  } catch {
    notFound();
  }

  if (!page) {
    notFound();
  }

  const jsonLdScript = page.json_ld
    ? `<script type="application/ld+json">${JSON.stringify(page.json_ld)}</script>`
    : null;

  return (
    <>
      {jsonLdScript && (
        <head dangerouslySetInnerHTML={{ __html: jsonLdScript }} />
      )}
      <main className="flex-1 px-3 md:px-6 lg:px-8 xl:px-12 pt-[100px] pb-16 space-y-8">
        {page.sections.filter((section) => section.is_visible).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)).map((section) => (
          <PublicSectionRenderer key={section.id} section={section} />
        ))}
      </main>
    </>
  );
}
