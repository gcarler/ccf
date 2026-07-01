"use client";

import React, { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ExternalLink, Loader2, Monitor, RefreshCw } from "lucide-react";
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";
import { useAuth } from "@/context/AuthContext";
import { getCmsPagePreview } from "@/lib/cms/v2";
import { SITE_KEY } from "@/lib/site-config";
import { CmsPublicPage } from "@/types/cms-v2";

const PREVIEW_TOKENS = {
  "--site-background": "#f8f9ff",
  "--site-on-background": "#101828",
  "--site-surface-container": "#ffffff",
  "--site-surface-container-low": "#f0f4ff",
  "--site-surface-container-high": "#e6ecff",
  "--site-surface-container-highest": "#d9e2ff",
  "--site-on-surface": "#101828",
  "--site-on-surface-variant": "#475467",
  "--site-primary": "#3155d4",
  "--site-on-primary": "#ffffff",
  "--site-primary-container": "#e1e8ff",
  "--site-on-primary-container": "#001a66",
  "--site-secondary": "#e0a931",
} as React.CSSProperties;

export default function CmsPreviewPage() {
  return (
    <Suspense fallback={
      <div className="flex h-full items-center justify-center gap-3 text-sm font-bold text-[hsl(var(--text-secondary))]">
        <Loader2 className="animate-spin" size={18} /> Cargando preview...
      </div>
    }>
      <CmsPreviewInner />
    </Suspense>
  );
}

function CmsPreviewInner() {
  const params = useSearchParams();
  const { token } = useAuth();
  const siteKey = params?.get("site") || SITE_KEY;
  const slug = params?.get("page") || "";
  const [page, setPage] = useState<CmsPublicPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const publicHref = useMemo(() => {
    const base = siteKey === SITE_KEY ? "/" : `/${siteKey}`;
    return slug ? `${base}/${slug}` : base;
  }, [siteKey, slug]);

  const loadPreview = async () => {
    if (!token || !slug) {
      setLoading(false);
      setPage(null);
      setError(!slug ? "Falta el parametro page." : "Inicia sesion para ver el preview.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getCmsPagePreview(siteKey, slug, token);
      setPage(data);
    } catch {
      setPage(null);
      setError("No se pudo cargar la vista previa.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteKey, slug, token]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[hsl(var(--surface-2))] dark:bg-[#0b0d11]">
      <header className="shrink-0 border-b border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-3 dark:border-white/10 dark:bg-[#111418]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Vista previa CMS</p>
            <h1 className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">{page?.title || slug || "Preview"}</h1>
            <p className="text-xs text-[hsl(var(--text-secondary))]">/{siteKey}/{slug}</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={loadPreview} className="inline-flex items-center gap-2 rounded-md border border-[hsl(var(--border))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:border-white/10 dark:text-[hsl(var(--text-secondary))]">
              <RefreshCw size={13} /> Recargar
            </button>
            <Link href={publicHref} target="_blank" className="inline-flex items-center gap-2 rounded-md bg-[hsl(var(--bg-muted))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white dark:bg-[hsl(var(--bg-primary))] dark:text-[hsl(var(--text-primary))]">
              <ExternalLink size={13} /> Publicado
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-4 md:p-4">
        <div className="mx-auto max-w-6xl overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] shadow-xl dark:border-white/10 dark:bg-[#0f1115]">
          <div className="flex items-center gap-2 border-b border-[hsl(var(--border))] px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:border-white/10">
            <Monitor size={13} /> Draft actual
          </div>
          <div style={PREVIEW_TOKENS} className="min-h-[70vh] px-3 py-1.5 md:px-4 lg:px-4 space-y-3">
            {loading ? (
              <div className="flex min-h-[320px] items-center justify-center gap-3 text-sm font-bold text-[hsl(var(--text-secondary))]">
                <Loader2 className="animate-spin" size={18} /> Cargando preview...
              </div>
            ) : error ? (
              <div className="min-h-[320px] rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-center text-sm font-bold text-[hsl(var(--text-secondary))]">
                {error}
              </div>
            ) : page ? (
              page.sections
                .filter((section) => section.is_visible)
                .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
                .map((section) => <PublicSectionRenderer key={section.id} section={section} />)
            ) : null}
          </div>
        </div>
      </main>
    </div>
  );
}
