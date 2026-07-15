"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { SITE_KEY, SITE_NAME } from "@/lib/site-config";
import { usePublicBootstrap } from "@/components/public/PublicBootstrapProvider";

export interface SiteBranding {
  logoUrl: string;
  logoName: string;
}

export function useSiteBranding(fallback?: Partial<SiteBranding>) {
  const bootstrapTheme = usePublicBootstrap()?.theme ?? null;
  const [branding, setBranding] = useState<SiteBranding>({
    logoUrl: bootstrapTheme?.tokens_json?.["--site-logo-url"] || fallback?.logoUrl || "",
    logoName: bootstrapTheme?.tokens_json?.["--site-logo-name"] || fallback?.logoName || SITE_NAME,
  });

  useEffect(() => {
    if (bootstrapTheme?.tokens_json) {
      setBranding({
        logoUrl: bootstrapTheme.tokens_json["--site-logo-url"] || fallback?.logoUrl || "",
        logoName: bootstrapTheme.tokens_json["--site-logo-name"] || fallback?.logoName || SITE_NAME,
      });
      return;
    }

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
  }, [bootstrapTheme?.tokens_json, fallback?.logoName, fallback?.logoUrl]);

  return branding;
}
