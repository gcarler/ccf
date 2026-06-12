"use client";

import React, { useEffect, useState } from "react";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { CmsPublicPage } from "@/types/cms-v2";
import PublicSectionRenderer from "./PublicSectionRenderer";

interface CmsPageOverrideProps {
  slug: string;
  children: React.ReactNode;
}

export default function CmsPageOverride({ slug, children }: CmsPageOverrideProps) {
  const [page, setPage] = useState<CmsPublicPage | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getCmsPublicPage("faro", slug)
      .then((data) => {
        if (active) {
          setPage(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setPage(null);
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--faro-background)" }}>
        <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--faro-primary) transparent var(--faro-primary) transparent" }}></div>
      </div>
    );
  }

  if (page && Array.isArray(page.sections) && page.sections.length > 0) {
    const visibleSections = page.sections
      .filter((s) => s.is_visible)
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

    return (
      <div className="space-y-8">
        {visibleSections.map((section) => (
          <PublicSectionRenderer key={section.id} section={section} />
        ))}
      </div>
    );
  }

  return <>{children}</>;
}
