import React from "react";
import { notFound } from "next/navigation";
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";
import { Metadata } from "next";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { CmsPublicPage } from "@/types/cms-v2";
import { FAROHeader, FAROFooter } from "@/components/public/FAROShared";

export async function generateMetadata({ params }: { params: Promise<{ slug: string[] }> }): Promise<Metadata> {
  const resolvedParams = await params;
  const slugValue = Array.isArray(resolvedParams?.slug) ? resolvedParams.slug.join("/") : "";
  if (!slugValue) return {};

  try {
    const page = await getCmsPublicPage("faro", slugValue);
    if (!page) return {};
    const seo = page.seo_json || {};
    const metaTitle = typeof seo.meta_title === "string" && seo.meta_title.trim() ? seo.meta_title : page.title;
    const metaDescription = typeof seo.meta_description === "string" && seo.meta_description.trim() ? seo.meta_description : undefined;
    const metaImage = typeof seo.meta_image === "string" && seo.meta_image.trim() ? seo.meta_image : undefined;
    return {
      title: metaTitle,
      description: metaDescription,
      openGraph: {
        title: metaTitle,
        description: metaDescription,
        images: metaImage ? [metaImage] : undefined,
      }
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
    page = await getCmsPublicPage("faro", slugValue);
  } catch {
    notFound();
  }

  if (!page) {
    notFound();
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--faro-background)", color: "var(--faro-on-background)" }}>
      <FAROHeader />
      <main className="flex-1 px-3 md:px-6 lg:px-8 xl:px-12 py-8 md:py-12 lg:py-16 space-y-8">
        {page.sections.filter((section) => section.is_visible).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)).map((section) => (
          <PublicSectionRenderer key={section.id} section={section} />
        ))}
      </main>
      <FAROFooter />
    </div>
  );
}
