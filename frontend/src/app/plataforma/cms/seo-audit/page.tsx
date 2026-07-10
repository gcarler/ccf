"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Eye,
  Gauge,
  Info,
  Layers3,
  Loader2,
  RefreshCcw,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { SITE_KEY } from "@/lib/site-config";
import SidePanel from "@/components/ui/SidePanel";
import { canEditCms } from "@/lib/cms/permissions";
import {
  PageSeoAudit,
  SeoAuditResponse,
  SiteSeoStats,
  getSeoAudit,
} from "@/lib/cms/v2";
import clsx from "clsx";

type StatusFilter = "all" | "published" | "draft" | "in_review" | "archived";

const SEVERITY_STYLES: Record<string, { tone: string; icon: typeof AlertCircle; label: string }> = {
  error: {
    tone: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300 border border-rose-200 dark:border-rose-500/30",
    icon: AlertCircle,
    label: "Error",
  },
  warning: {
    tone: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300 border border-amber-200 dark:border-amber-500/30",
    icon: AlertTriangle,
    label: "Advertencia",
  },
  info: {
    tone: "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300 border border-blue-200 dark:border-blue-500/30",
    icon: Info,
    label: "Info",
  },
};

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "published", label: "Publicado" },
  { value: "draft", label: "Borrador" },
  { value: "in_review", label: "En revisión" },
  { value: "archived", label: "Archivado" },
];

function scoreTone(score: number): {
  bg: string;
  text: string;
  ring: string;
  label: string;
} {
  if (score >= 80) {
    return {
      bg: "bg-emerald-100 dark:bg-emerald-500/15",
      text: "text-emerald-700 dark:text-emerald-300",
      ring: "ring-emerald-300 dark:ring-emerald-500/40",
      label: "Excelente",
    };
  }
  if (score >= 50) {
    return {
      bg: "bg-amber-100 dark:bg-amber-500/15",
      text: "text-amber-700 dark:text-amber-300",
      ring: "ring-amber-300 dark:ring-amber-500/40",
      label: "Atención",
    };
  }
  return {
    bg: "bg-rose-100 dark:bg-rose-500/15",
    text: "text-rose-700 dark:text-rose-300",
    ring: "ring-rose-300 dark:ring-rose-500/40",
    label: "Crítico",
  };
}

function severityIcon(severity: string) {
  return SEVERITY_STYLES[severity]?.icon ?? Info;
}

function severityToneChip(severity: string) {
  return (
    SEVERITY_STYLES[severity] ??
    SEVERITY_STYLES.info
  );
}

function metric(value: number | undefined, loading: boolean): string {
  if (loading) return "...";
  return value === undefined || value === null ? "0" : String(value);
}

export default function CmsSeoAuditPage() {
  const router = useRouter();
  const { token, user } = useAuth();
  const [siteKey] = useState<string>(SITE_KEY);
  const [audit, setAudit] = useState<SeoAuditResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [minScore, setMinScore] = useState<number | "">("");
  const [selectedPage, setSelectedPage] = useState<PageSeoAudit | null>(null);
  const canEdit = canEditCms(user?.role);

  const fetchAudit = async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const opts: Parameters<typeof getSeoAudit>[1] = {};
      if (statusFilter !== "all") opts.status = statusFilter;
      if (typeof minScore === "number") opts.min_score = minScore;
      const data = await getSeoAudit(siteKey, opts, token);
      setAudit(data);
    } catch (error) {
      toast.error("Error fetching SEO audit");
      toast.error("No se pudo cargar el audit SEO del sitio");
      setAudit(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit().catch(() => toast.error("Error al cargar auditoría"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, siteKey, statusFilter, minScore]);

  const aggregate: SiteSeoStats | undefined = audit?.aggregate;

  const filteredPages = useMemo(() => {
    if (!audit?.pages) return [];
    const term = search.trim().toLowerCase();
    if (!term) return audit.pages;
    return audit.pages.filter(
      (page) =>
        page.title.toLowerCase().includes(term) ||
        page.slug.toLowerCase().includes(term),
    );
  }, [audit, search]);

  const openPageInBuilder = (page: PageSeoAudit) => {
    router.push(`/cms/builder?site=${siteKey}&page=${page.slug}`);
  };

  const openSectionInBuilder = (page: PageSeoAudit, sectionId: string) => {
    // Drawer-stack-consistent (AGENTS_FRONTEND.md §3): navegar dentro del
    // mismo tab con el builder deep-link a la sección afectada.
    router.push(
      `/cms/builder?site=${siteKey}&page=${page.slug}&section=${sectionId}`,
    );
  };

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
      <header className="h-12 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-4 gap-3 shrink-0">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Gauge size={16} className="text-[hsl(var(--primary))] shrink-0" />
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] truncate">
            Auditoría SEO
          </h2>
          <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full">
            {audit?.pages?.length ?? 0} páginas
          </span>
        </div>

        <button
          type="button"
          onClick={() => fetchAudit().catch(() => toast.error("Error al cargar auditoría"))}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 hover:border-[hsl(var(--primary))] dark:hover:border-[hsl(var(--primary))] text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] disabled:opacity-40 transition-colors"
          title="Refrescar"
        >
          <RefreshCcw size={12} className={loading ? "animate-spin" : ""} />
          Refrescar
        </button>
      </header>

      <div className="flex-1 overflow-y-auto custom-scrollbar px-4 py-3 space-y-3">
        {loading && !audit && (
          <div className="flex items-center justify-center gap-2 py-1.5 text-sm text-[hsl(var(--text-secondary))]">
            <Loader2 size={14} className="animate-spin" /> Calculando audit…
          </div>
        )}

        {!loading && audit && (
          <>
            {/* Hero / Aggregate */}
            <section className="grid grid-cols-1 gap-3 lg:grid-cols-4">
              <ScoreCard aggregate={aggregate} loading={loading} />
              <StatCard
                label="Páginas auditadas"
                value={metric(aggregate?.total_pages, loading)}
                icon={Layers3}
                hint="Paginadas a 50; ajustar en la API"
              />
              <StatCard
                label="Hallazgos críticos"
                value={metric(aggregate?.critical_issues, loading)}
                icon={AlertCircle}
                tone="bg-rose-50 dark:bg-rose-500/15 text-rose-700 dark:text-rose-300"
              />
              <StatCard
                label="Páginas con errores"
                value={metric(aggregate?.pages_with_errors, loading)}
                icon={ShieldCheck}
                tone="bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300"
              />
            </section>

            {/* By severity spot */}
            <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {(["error", "warning", "info"] as const).map((sev) => (
                <div
                  key={sev}
                  className={clsx(
                    "rounded-lg px-4 py-3 flex items-center gap-3",
                    severityToneChip(sev).tone,
                  )}
                >
                  {React.createElement(severityIcon(sev), { size: 18 })}
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide opacity-80">
                      {severityToneChip(sev).label}
                    </p>
                    <p className="text-2xl font-bold">
                      {metric(aggregate?.by_severity?.[sev], loading)}
                    </p>
                  </div>
                </div>
              ))}
            </section>

            {/* Filter bar */}
            <section className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="relative flex-1 max-w-md">
                <Search
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
                />
                <input
                  type="text"
                  placeholder="Buscar páginas o slugs…"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 border border-transparent focus:border-[hsl(var(--primary))] rounded-lg text-[13px] focus:ring-0 outline-none"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
                className="px-3 py-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg text-[12px] border border-transparent focus:border-[hsl(var(--primary))]"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              <div className="flex items-center gap-2">
                <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                  Score mínimo
                </label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={minScore}
                  onChange={(event) =>
                    setMinScore(
                      event.target.value === ""
                        ? ""
                        : Number.parseInt(event.target.value, 10) || 0,
                    )
                  }
                  className="w-16 px-2 py-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg text-[12px] border border-transparent focus:border-[hsl(var(--primary))]"
                />
              </div>
            </section>

            {/* Page list */}
            <section className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[#111418] overflow-hidden">
              {filteredPages.length === 0 ? (
                <div className="px-6 py-1.5 text-center">
                  <Sparkles
                    size={32}
                    className="mx-auto mb-3 text-[hsl(var(--primary))]"
                  />
                  <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">
                    {search
                      ? "Sin páginas para mostrar"
                      : "No hay páginas que auditar"}
                  </p>
                  <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
                    {search
                      ? "Intente con otro término o quite el filtro."
                      : "Cree la primera página desde el menú CMS > Pages."}
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                  {filteredPages.map((page) => {
                    const tone = scoreTone(page.score);
                    const isCritical = page.findings.some(
                      (finding) => finding.severity === "error",
                    );
                    return (
                      <button
                        key={page.page_id}
                        onClick={() => setSelectedPage(page)}
                        className="w-full flex items-center gap-4 px-4 py-3 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/[0.03] transition-colors text-left"
                      >
                        <div
                          className={clsx(
                            "size-8 rounded-lg flex items-center justify-center shrink-0",
                            tone.bg,
                            tone.text,
                          )}
                        >
                          <span className="text-sm font-bold">{page.score}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">
                              {page.title}
                            </p>
                            <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full shrink-0">
                              {page.status}
                            </span>
                          </div>
                          <p className="text-[11px] text-[hsl(var(--text-secondary))] truncate">
                            /{page.slug} · {page.findings.length} hallazgos
                          </p>
                        </div>
                        {isCritical && (
                          <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-500/15 border border-rose-200 dark:border-rose-500/30 px-2 py-1 rounded-full">
                            <AlertCircle size={11} /> Crítico
                          </span>
                        )}
                        <ArrowRight
                          size={14}
                          className="text-[hsl(var(--text-secondary))] shrink-0"
                        />
                      </button>
                    );
                  })}
                </div>
              )}
            </section>

            <p className="text-[11px] text-[hsl(var(--text-secondary))] text-center">
              Auditoría basada en el estado actual del CMS. Los hallazgos críticos y
              warnings se actualizan al refrescar; corríjalos en el builder o en la
              configuración de cada página.
            </p>
          </>
        )}
      </div>

      <SidePanel
        isOpen={!!selectedPage}
        onClose={() => setSelectedPage(null)}
        title={selectedPage?.title ?? ""}
        subtitle={selectedPage ? `/${selectedPage.slug}` : undefined}
        fullViewHref={
          selectedPage && canEdit
            ? `/cms/builder?site=${siteKey}&page=${selectedPage.slug}`
            : undefined
        }
      >
        {selectedPage && (
          <div className="space-y-4">
            {/* Score card */}
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className={clsx(
                "rounded-lg p-4 flex items-center gap-4 ring-1",
                scoreTone(selectedPage.score).bg,
                scoreTone(selectedPage.score).text,
                scoreTone(selectedPage.score).ring,
              )}
            >
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide opacity-75">
                  Score SEO
                </p>
                <p className="text-3xl font-bold leading-tight">
                  {selectedPage.score}
                </p>
                <p className="text-[10px] font-semibold uppercase tracking-wide opacity-80 mt-1">
                  {scoreTone(selectedPage.score).label}
                </p>
              </div>
              <div className="flex-1 text-right text-[11px] leading-relaxed opacity-80">
                {selectedPage.findings.length === 0
                  ? "Sin hallazgos. Auditoría limpia para esta página."
                  : `${selectedPage.findings.length} hallazgo${selectedPage.findings.length === 1 ? "" : "s"} que requieren atención`}
              </div>
            </motion.div>

            {selectedPage.findings.length === 0 && (
              <div className="rounded-lg border border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/10 p-4 text-emerald-700 dark:text-emerald-300 flex items-center gap-3">
                <CheckCircle2 size={18} />
                <p className="text-sm font-medium">
                  La página cumple con todas las validaciones SEO del audit
                  actual.
                </p>
              </div>
            )}

            <ul className="space-y-3">
              {selectedPage.findings.map((finding) => {
                const Icon = severityIcon(finding.severity);
                const wrapper = SEVERITY_STYLES[finding.severity] ?? SEVERITY_STYLES.info;
                const hasBuilderLink = Boolean(finding.section_id);
                return (
                  <li
                    key={finding.code}
                    className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1f]"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={clsx(
                          "size-8 rounded-lg flex items-center justify-center shrink-0",
                          wrapper.tone,
                        )}
                      >
                        <Icon size={16} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-[12px] font-bold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white">
                            {finding.code.replace(/_/g, " ")}
                          </p>
                          <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full">
                            -{finding.impact_points} pts
                          </span>
                        </div>
                        <p className="mt-1 text-[12px] text-[hsl(var(--text-secondary))] leading-relaxed">
                          {finding.message}
                        </p>
                        <p className="mt-2 text-[11px] font-medium text-[hsl(var(--primary))]">
                          Sugerencia: {finding.hint}
                        </p>
                        {finding.field_ref && (
                          <p className="mt-1 text-[10px] font-mono text-[hsl(var(--text-secondary))]">
                            {finding.field_ref}
                          </p>
                        )}
                        {hasBuilderLink && finding.section_id && canEdit && (
                          <button
                            type="button"
                            onClick={() =>
                              openSectionInBuilder(selectedPage, finding.section_id!)
                            }
                            className="mt-2 inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] hover:underline"
                          >
                            <Eye size={10} /> Abrir sección en builder
                          </button>
                        )}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>

            <div className="pt-4 border-t border-[hsl(var(--border))] dark:border-white/5">
              {canEdit ? (
                <button
                  type="button"
                  onClick={() => openPageInBuilder(selectedPage)}
                  className="w-full bg-[hsl(var(--primary))] text-white px-3 py-2.5 rounded-lg text-[11px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--primary))]/90 active:scale-[0.98] transition-all"
                >
                  Ir al builder de la página
                </button>
              ) : (
                <Link
                  href="/cms/pages"
                  className="block w-full text-center px-3 py-2.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--primary))] hover:text-[hsl(var(--primary))]"
                >
                  Ver listado completo en /cms/pages
                </Link>
              )}
            </div>
          </div>
        )}
      </SidePanel>
    </div>
  );
}

function ScoreCard({
  aggregate,
  loading,
}: {
  aggregate: SiteSeoStats | undefined;
  loading: boolean;
}) {
  const score = aggregate?.average_score ?? 0;
  const tone = scoreTone(score);
  return (
    <div
      className={clsx(
        "rounded-lg p-4 ring-1 col-span-1 lg:col-span-1 flex items-center gap-4",
        tone.bg,
        tone.text,
        tone.ring,
      )}
    >
      <div className="relative size-14 shrink-0 flex items-center justify-center">
        <svg className="absolute inset-0 -rotate-90" viewBox="0 0 56 56">
          <circle
            cx="28"
            cy="28"
            r="24"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            className="opacity-20"
          />
          <circle
            cx="28"
            cy="28"
            r="24"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            strokeDasharray={`${2 * Math.PI * 24}`}
            strokeDashoffset={`${2 * Math.PI * 24 * (1 - score / 100)}`}
            strokeLinecap="round"
          />
        </svg>
        <span className="text-lg font-bold">{loading ? "..." : score}</span>
      </div>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wide opacity-80">
          Score promedio
        </p>
        <p className="text-xl font-bold leading-tight">{tone.label}</p>
        <p className="text-[11px] opacity-80 mt-1">
          Faro global · {aggregate?.total_pages ?? 0} páginas
        </p>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone,
  hint,
}: {
  label: string;
  value: string;
  icon: typeof Gauge;
  tone?: string;
  hint?: string;
}) {
  return (
    <div
      className={clsx(
        "rounded-lg p-4 border",
        tone
          ? tone
          : "border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418]",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
          {label}
        </p>
        <Icon size={14} className="text-[hsl(var(--text-secondary))]" />
      </div>
      <p className="mt-2 text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">
        {value}
      </p>
      {hint && (
        <p className="mt-1 text-[10px] text-[hsl(var(--text-secondary))]">
          {hint}
        </p>
      )}
    </div>
  );
}
