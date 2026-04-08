import React from "react";
import { notFound } from "next/navigation";
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { CmsPublicPage } from "@/types/cms-v2";

export default async function FaroDynamicPage({ params }: { params: { slug: string[] } }) {
  const slugValue = Array.isArray(params?.slug) ? params.slug.join("/") : "";

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
    <main className="px-6 md:px-12 lg:px-20 py-28 space-y-8" style={{ background: "var(--faro-background)", color: "var(--faro-on-background)" }}>
      {page.sections.filter((section) => section.is_visible).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)).map((section) => (
        <PublicSectionRenderer key={section.id} section={section} />
      ))}
    </main>
  );
}
