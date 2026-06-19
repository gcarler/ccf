"use client";

import React, { useEffect, useState } from "react";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { SITE_KEY } from "@/lib/site-config";
import { CmsPublicPage } from "@/types/cms-v2";
import PublicSectionRenderer from "./PublicSectionRenderer";

interface CmsPageOverrideProps {
  slug: string;
  children: React.ReactNode;
}

export default function CmsPageOverride({ slug, children }: CmsPageOverrideProps) {
  const [page, setPage] = useState<CmsPublicPage | null>(null);

  useEffect(() => {
    let active = true;
    getCmsPublicPage(SITE_KEY, slug, { silent: true })
      .then((data) => {
        if (active) {
          setPage(data);
        }
      })
      .catch(() => {
        if (active) {
          setPage(null);
        }
      });
    return () => {
      active = false;
    };
  }, [slug]);

  if (page && Array.isArray(page.sections) && page.sections.length > 0) {
    const visibleSections = page.sections
      .filter((s) => s.is_visible)
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

    if (visibleSections.length > 0) {
      return (
        <div className="space-y-8">
          {visibleSections.map((section) => (
            <PublicSectionRenderer key={section.id} section={section} />
          ))}
        </div>
      );
    }
  }

  return <>{children}</>;
}
