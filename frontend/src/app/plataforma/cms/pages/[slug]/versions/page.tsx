"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ChevronDown, History, Loader2, RefreshCw, RotateCcw } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { SITE_KEY } from "@/lib/site-config";
import {
  listCmsPageVersions,
  rollbackCmsPageVersion,
  listCmsPages,
  listCmsSites,
} from "@/lib/cms/v2";
import { CmsPageVersion, CmsSite } from "@/types/cms-v2";
import { canPublishCms } from "@/lib/cms/permissions";
import { diffPageVersionSnapshots } from "@/lib/cms/versionDiff";
import { VersionsDiffView } from "./VersionsDiffView";

type PageVersionSnapshot = {
  page?: Record<string, unknown>;
  sections?: Array<Record<string, unknown>>;
};

export default function PageVersionsDiffPage() {
  const params = useParams();
  const router = useRouter();
  const { token, user } = useAuth();
  const slug = (params?.slug as string) || "";

  const [siteKey, setSiteKey] = useState<string>(SITE_KEY);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [versions, setVersions] = useState<CmsPageVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [versionAId, setVersionAId] = useState<string | null>(null);
  const [versionBId, setVersionBId] = useState<string | null>(null);
  const [rollingBack, setRollingBack] = useState(false);
  const [hideUnchanged, setHideUnchanged] = useState<boolean>(true);

  // ── Load sites + versions ─────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const [nextSites] = await Promise.all([listCmsSites(token)]);
        if (cancelled) return;
        const list = nextSites || [];
        setSites(list);
        if (list.length > 0 && !list.find((s) => s.site_key === siteKey)) {
          setSiteKey(list[0].site_key);
        }
      } catch {
        // Non-fatal — we still try to load versions with the current siteKey.
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Reset version selections whenever the user changes the page or
  // the site. The previously selected ids belong to a different
  // site/slug's version list and would otherwise leak into the new
  // picker's options, surfacing as "phantom" selections.
  useEffect(() => {
    setVersionAId(null);
    setVersionBId(null);
  }, [siteKey, slug]);

  useEffect(() => {
    if (!token || !siteKey || !slug) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [nextVersions, nextPages] = await Promise.all([
          listCmsPageVersions(siteKey, slug, token),
          listCmsPages(siteKey, token).catch(() => []),
        ]);
        if (cancelled) return;
        const list = (nextVersions || []).slice().sort(
          (x, y) => y.version_number - x.version_number,
        );
        setVersions(list);
        // Default to "second-to-last vs last" so the editor opens the
        // most recent meaningful change. No ``??`` here: we always
        // re-pick on a fresh fetch because the previous ids are now
        // intentionally cleared by the effect above.
        if (list.length >= 2) {
          setVersionAId(list[1].id);
          setVersionBId(list[0].id);
        } else if (list.length === 1) {
          setVersionAId(list[0].id);
          setVersionBId(list[0].id);
        }
        if ((nextPages || []).length === 0) {
          // Soft warning — versions may still exist for a different slug.
          toast.warning(`No se encontró la página "/${slug}" en ${siteKey}.`);
        }
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : "Error al cargar versiones";
        setError(msg);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, siteKey, slug]);

  // ── Selected pair ────────────────────────────────────────────────
  const versionA = useMemo(
    () => versions.find((v) => v.id === versionAId) ?? null,
    [versions, versionAId],
  );
  const versionB = useMemo(
    () => versions.find((v) => v.id === versionBId) ?? null,
    [versions, versionBId],
  );

  const diff = useMemo(() => {
    if (!versionA || !versionB) return null;
    return diffPageVersionSnapshots(
      (versionA.snapshot_json as PageVersionSnapshot | null) || {},
      (versionB.snapshot_json as PageVersionSnapshot | null) || {},
    );
  }, [versionA, versionB]);

  const canRollback = canPublishCms(user?.role);

  // ── Handlers ─────────────────────────────────────────────────────
  const reload = async () => {
    if (!token || !siteKey || !slug) return;
    setLoading(true);
    setError(null);
    try {
      const nextVersions = await listCmsPageVersions(siteKey, slug, token);
      const list = (nextVersions || []).slice().sort(
        (x, y) => y.version_number - x.version_number,
      );
      setVersions(list);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al recargar";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (versionId: string) => {
    if (!token || !siteKey || !slug || !canRollback) return;
    if (!confirm("¿Restaurar esta versión? Las secciones actuales serán reemplazadas.")) return;
    setRollingBack(true);
    try {
      await rollbackCmsPageVersion(siteKey, slug, versionId, token);
      toast.success("Versión restaurada como borrador");
      await reload();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al restaurar";
      toast.error(msg);
    } finally {
      setRollingBack(false);
    }
  };

  const goToBuilder = () => {
    router.push(`/cms/builder?site=${siteKey}&page=${slug}`);
  };

  // ── Render ───────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))]">
      <Header
        siteKey={siteKey}
        sites={sites}
        onSiteKeyChange={setSiteKey}
        slug={slug}
        loading={loading}
        onReload={reload}
        onBackToBuilder={goToBuilder}
      />
      <VersionToolbar
        versions={versions}
        versionAId={versionAId}
        versionBId={versionBId}
        onChangeA={setVersionAId}
        onChangeB={setVersionBId}
        disabled={loading}
      />
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
        {loading && (
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-[hsl(var(--text-secondary))]">
            <Loader2 size={28} className="animate-spin" />
            <p className="text-[12px]">Cargando versiones…</p>
          </div>
        )}
        {error && !loading && (
          <div className="rounded-lg border border-rose-200 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/10 p-4 text-rose-800 dark:text-rose-200 text-[12px]">
            <p className="font-semibold mb-1">No se pudieron cargar las versiones</p>
            <p className="opacity-80">{error}</p>
          </div>
        )}
        {!loading && !error && versions.length === 0 && (
          <EmptyState slug={slug} siteKey={siteKey} onBackToBuilder={goToBuilder} />
        )}
        {!loading && !error && versions.length === 1 && (
          <SingleVersionState version={versions[0]} onBackToBuilder={goToBuilder} />
        )}
        {!loading && !error && diff && versionA && versionB && (
          <AnimatePresence mode="wait">
            <motion.div
              key={`${versionA.id}::${versionB.id}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <VersionsDiffView
                before={versionA}
                after={versionB}
                diff={diff}
                canRollback={canRollback}
                onRollback={handleRollback}
                hideUnchanged={hideUnchanged}
                onToggleHideUnchanged={() => setHideUnchanged((v) => !v)}
              />
            </motion.div>
          </AnimatePresence>
        )}
      </div>
      {rollingBack && (
        <div className="fixed bottom-4 right-4 z-50 inline-flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50 dark:bg-amber-500/10 px-3 py-2 text-[12px] text-amber-800 dark:text-amber-200 shadow-lg">
          <Loader2 size={14} className="animate-spin" /> Restaurando versión…
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────

function Header({
  siteKey,
  sites,
  onSiteKeyChange,
  slug,
  loading,
  onReload,
  onBackToBuilder,
}: {
  siteKey: string;
  sites: CmsSite[];
  onSiteKeyChange: (k: string) => void;
  slug: string;
  loading: boolean;
  onReload: () => void;
  onBackToBuilder: () => void;
}) {
  return (
    <header className="h-12 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-4 gap-3 shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))]">
      <button
        onClick={onBackToBuilder}
        className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
      >
        <ArrowLeft size={14} /> Volver al builder
      </button>
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <History size={16} className="text-[hsl(var(--primary))] shrink-0" />
        <h1 className="text-[12px] font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white truncate">
          Diff de versiones — /{slug}
        </h1>
      </div>
      <select
        value={siteKey}
        onChange={(e) => onSiteKeyChange(e.target.value)}
        className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2.5 py-1 text-[12px]"
      >
        {sites.length === 0 && <option value={SITE_KEY}>{SITE_KEY}</option>}
        {sites.map((s) => (
          <option key={s.id} value={s.site_key}>
            {s.name} ({s.site_key})
          </option>
        ))}
      </select>
      <button
        onClick={onReload}
        disabled={loading}
        className="inline-flex items-center gap-1.5 rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all disabled:opacity-50"
      >
        <RefreshCw size={12} className={loading ? "animate-spin" : ""} /> Recargar
      </button>
    </header>
  );
}

function VersionToolbar({
  versions,
  versionAId,
  versionBId,
  onChangeA,
  onChangeB,
  disabled,
}: {
  versions: CmsPageVersion[];
  versionAId: string | null;
  versionBId: string | null;
  onChangeA: (id: string) => void;
  onChangeB: (id: string) => void;
  disabled: boolean;
}) {
  if (versions.length < 2) return null;
  return (
    <div className="h-10 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-4 gap-3 shrink-0 bg-[hsl(var(--surface-1))] dark:bg-white/[0.02]">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
        Comparar
      </span>
      <VersionPicker
        label="A (base)"
        versions={versions}
        value={versionAId}
        onChange={onChangeA}
        disabled={disabled}
        accent="rose"
      />
      <span className="text-[hsl(var(--text-secondary))]">→</span>
      <VersionPicker
        label="B (cambio)"
        versions={versions}
        value={versionBId}
        onChange={onChangeB}
        disabled={disabled}
        accent="emerald"
      />
    </div>
  );
}

function VersionPicker({
  label,
  versions,
  value,
  onChange,
  disabled,
  accent,
}: {
  label: string;
  versions: CmsPageVersion[];
  value: string | null;
  onChange: (id: string) => void;
  disabled: boolean;
  accent: "rose" | "emerald";
}) {
  const current = versions.find((v) => v.id === value) ?? null;
  return (
    <div
      className={clsx(
        "relative inline-flex items-center gap-1.5 rounded-md border px-2 py-1",
        accent === "rose"
          ? "border-rose-200 dark:border-rose-500/30 bg-rose-50/60 dark:bg-rose-500/5"
          : "border-emerald-200 dark:border-emerald-500/30 bg-emerald-50/60 dark:bg-emerald-500/5",
      )}
    >
      <span className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
        {label}
      </span>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="appearance-none bg-transparent pr-5 pl-1 text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-white focus:outline-none"
      >
        {versions.map((v) => (
          <option key={v.id} value={v.id}>
            v{v.version_number} · {new Date(v.created_at).toLocaleString()}
          </option>
        ))}
      </select>
      <ChevronDown size={12} className="absolute right-2 pointer-events-none text-[hsl(var(--text-secondary))]" />
      {current?.notes && (
        <span className="hidden md:inline text-[10px] italic text-[hsl(var(--text-secondary))] max-w-[200px] truncate">
          — {current.notes}
        </span>
      )}
    </div>
  );
}

function EmptyState({
  slug,
  siteKey,
  onBackToBuilder,
}: {
  slug: string;
  siteKey: string;
  onBackToBuilder: () => void;
}) {
  return (
    <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/10 p-8 text-center space-y-3">
      <div className="inline-flex size-10 items-center justify-center rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))]">
        <History size={20} />
      </div>
      <p className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-white">
        Esta página aún no tiene versiones publicadas
      </p>
      <p className="text-[12px] text-[hsl(var(--text-secondary))] max-w-md mx-auto">
        Las versiones se generan automáticamente cada vez que publicas la página{" "}
        <span className="font-mono">/{slug}</span> en <span className="font-mono">{siteKey}</span>.
        Vuelve después de la primera publicación para ver el diff.
      </p>
      <button
        onClick={onBackToBuilder}
        className="inline-flex items-center gap-1.5 mt-2 rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
      >
        <ArrowLeft size={12} /> Ir al builder
      </button>
    </div>
  );
}

function SingleVersionState({
  version,
  onBackToBuilder,
}: {
  version: CmsPageVersion;
  onBackToBuilder: () => void;
}) {
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-6 space-y-3">
      <div className="flex items-center gap-2">
        <History size={16} className="text-[hsl(var(--primary))]" />
        <p className="text-[12px] font-semibold uppercase tracking-wider text-[hsl(var(--text-primary))] dark:text-white">
          Solo hay una versión publicada
        </p>
      </div>
      <p className="text-[12px] text-[hsl(var(--text-secondary))]">
        La versión <span className="font-mono">#{version.version_number}</span> del{" "}
        {new Date(version.created_at).toLocaleString()} es la única referencia. Publica de nuevo
        para empezar a comparar.
      </p>
      <button
        onClick={onBackToBuilder}
        className="inline-flex items-center gap-1.5 rounded-md bg-[hsl(var(--primary))] text-white px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:opacity-90"
      >
        <RotateCcw size={12} /> Ir al builder
      </button>
    </div>
  );
}
