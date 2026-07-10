"use client";

import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ExternalLink, Loader2, Monitor, RefreshCw, Pause, Play } from "lucide-react";
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";
import { useAuth } from "@/context/AuthContext";
import { getCmsPagePreview } from "@/lib/cms/v2";
import { apiFetch } from "@/lib/http";
import { SITE_KEY } from "@/lib/site-config";
import { CmsPublicPage, CmsTheme } from "@/types/cms-v2";

const POLL_INTERVAL_MS = 4000;

const FALLBACK_TOKENS = {
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
  const [themeTokens, setThemeTokens] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const publicHref = useMemo(() => {
    const base = siteKey === SITE_KEY ? "/" : `/${siteKey}`;
    return slug ? `${base}/${slug}` : base;
  }, [siteKey, slug]);

  const previewTokens = useMemo(() => {
    return { ...FALLBACK_TOKENS, ...themeTokens } as React.CSSProperties;
  }, [themeTokens]);

  const loadPreview = useCallback(async (silent = false) => {
    if (!token || !slug) {
      setLoading(false);
      setPage(null);
      setError(!slug ? "Falta el parametro page." : "Inicia sesion para ver el preview.");
      return;
    }
    if (!silent) setLoading(true);
    setError(null);
    if (!silent) setThemeTokens({});
    try {
      const [data, theme] = await Promise.all([
        getCmsPagePreview(siteKey, slug, token),
        apiFetch<CmsTheme>(`/cms/v2/public/sites/${siteKey}/theme`, { silent: true }).catch(() => null),
      ]);
      setPage(data);
      if (theme?.tokens_json) {
        setThemeTokens(theme.tokens_json);
      }
      setLastRefresh(new Date());
    } catch {
      if (!silent) {
        setPage(null);
        setError("No se pudo cargar la vista previa.");
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, [siteKey, slug, token]);

  // Initial load
  useEffect(() => {
    loadPreview();
  }, [loadPreview]);

  // Auto-refresh polling
  useEffect(() => {
    if (!autoRefresh || !token || !slug) return;

    const interval = setInterval(() => {
      loadPreview(true);
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [autoRefresh, token, slug, loadPreview]);

  // Pause auto-refresh when tab is hidden
  useEffect(() => {
    const handleVisibility = () => {
      if (document.hidden && autoRefresh) {
        setAutoRefresh(false);
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [autoRefresh]);

  const timeSinceRefresh = useMemo(() => {
    const seconds = Math.floor((Date.now() - lastRefresh.getTime()) / 1000);
    if (seconds < 5) return "ahora";
    if (seconds < 60) return `hace ${seconds}s`;
    return `hace ${Math.floor(seconds / 60)}m`;
  }, [lastRefresh, autoRefresh]);

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
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wide transition-colors ${
                autoRefresh
                  ? "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                  : "border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] dark:border-white/10"
              }`}
              title={autoRefresh ? "Pausar auto-refresh" : "Activar auto-refresh"}
            >
              {autoRefresh ? <Pause size={11} /> : <Play size={11} />}
              {autoRefresh ? `Auto ${timeSinceRefresh}` : "Pausado"}
            </button>
            <button onClick={() => loadPreview(false)} className="inline-flex items-center gap-2 rounded-md border border-[hsl(var(--border))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:border-white/10 dark:text-[hsl(var(--text-secondary))]">
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
            {autoRefresh && <span className="ml-auto text-emerald-600 dark:text-emerald-400">● Auto-refresh activo</span>}
          </div>
          <div style={previewTokens} className="min-h-[70vh] px-3 py-1.5 md:px-4 lg:px-4 space-y-3">
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
