"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ExternalLink, Loader2, Monitor, RefreshCw } from "lucide-react";
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";
import { useAuth } from "@/context/AuthContext";
import { getCmsPagePreview } from "@/lib/cms/v2";
import { CmsPublicPage } from "@/types/cms-v2";

const PREVIEW_TOKENS = {
  "--faro-background": "#f8f9ff",
  "--faro-on-background": "#101828",
  "--faro-surface-container": "#ffffff",
  "--faro-surface-container-low": "#f0f4ff",
  "--faro-surface-container-high": "#e6ecff",
  "--faro-surface-container-highest": "#d9e2ff",
  "--faro-on-surface": "#101828",
  "--faro-on-surface-variant": "#475467",
  "--faro-primary": "#3155d4",
  "--faro-on-primary": "#ffffff",
  "--faro-primary-container": "#e1e8ff",
  "--faro-on-primary-container": "#001a66",
  "--faro-secondary": "#e0a931",
} as React.CSSProperties;

export default function CmsPreviewPage() {
  const params = useSearchParams();
  const { token } = useAuth();
  const siteKey = params?.get("site") || "faro";
  const slug = params?.get("page") || "";
  const [page, setPage] = useState<CmsPublicPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const publicHref = useMemo(() => {
    const base = siteKey === "faro" ? "/faro" : `/${siteKey}`;
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
    <div className="flex h-full flex-col overflow-hidden bg-slate-100 dark:bg-[#0b0d11]">
      <header className="shrink-0 border-b border-slate-200 bg-white px-5 py-3 dark:border-white/10 dark:bg-[#111418]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-600">Vista previa CMS</p>
            <h1 className="text-lg font-semibold text-slate-900 dark:text-white">{page?.title || slug || "Preview"}</h1>
            <p className="text-xs text-slate-500">/{siteKey}/{slug}</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={loadPreview} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:border-white/10 dark:text-slate-300">
              <RefreshCw size={13} /> Recargar
            </button>
            <Link href={publicHref} target="_blank" className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white dark:bg-white dark:text-slate-900">
              <ExternalLink size={13} /> Publicado
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-4 md:p-8">
        <div className="mx-auto max-w-6xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl dark:border-white/10 dark:bg-[#0f1115]">
          <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:border-white/10">
            <Monitor size={13} /> Draft actual
          </div>
          <div style={PREVIEW_TOKENS} className="min-h-[70vh] px-6 py-10 md:px-12 lg:px-16 space-y-8">
            {loading ? (
              <div className="flex min-h-[320px] items-center justify-center gap-3 text-sm font-bold text-slate-400">
                <Loader2 className="animate-spin" size={18} /> Cargando preview...
              </div>
            ) : error ? (
              <div className="min-h-[320px] rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm font-bold text-slate-500">
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
