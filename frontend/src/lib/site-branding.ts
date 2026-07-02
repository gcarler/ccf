"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { SITE_KEY, SITE_NAME } from "@/lib/site-config";

export interface SiteBranding {
  logoUrl: string;
  logoName: string;
}

export function useSiteBranding(fallback?: Partial<SiteBranding>) {
  const [branding, setBranding] = useState<SiteBranding>({
    logoUrl: fallback?.logoUrl || "",
    logoName: fallback?.logoName || SITE_NAME,
  });

  useEffect(() => {
    let mounted = true;

    const load = async () => {
      try {
        const row = await apiFetch<{ tokens_json?: Record<string, string> }>(
          `/cms/v2/public/sites/${SITE_KEY}/theme`,
          { silent: true },
        );
        if (!mounted) return;

        const tokens = row?.tokens_json || {};
        setBranding({
          logoUrl: tokens["--site-logo-url"] || fallback?.logoUrl || "",
          logoName: tokens["--site-logo-name"] || fallback?.logoName || SITE_NAME,
        });
      } catch {
        if (!mounted) return;
        setBranding({
          logoUrl: fallback?.logoUrl || "",
          logoName: fallback?.logoName || SITE_NAME,
        });
      }
    };

    load();
    return () => {
      mounted = false;
    };
  }, [fallback?.logoName, fallback?.logoUrl]);

  return branding;
}
