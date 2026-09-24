"use client";

import React from "react";
import clsx from "clsx";
import { ArrowDown, ArrowRight, ArrowUp, Check, Edit3, Eye, EyeOff, FileText, GitCompare, type LucideIcon, Minus, Plus, Trash2 } from "lucide-react";
import { motion } from "framer-motion";
import {
 filterSemanticPropDiffs,
 humanizeFieldName,
 type FieldDiff,
 type PageVersionDiff,
 type SectionDiff as SectionDiffT,
} from "@/lib/cms/versionDiff";
import type { CmsPageVersion } from "@/types/cms-v2";
import { FieldDiffRow } from "./FieldDiff";

/**
 * Top-level side-by-side diff surface. Consumes a precomputed
 * ``PageVersionDiff`` (built once from the two ``CmsPageVersion``
 * snapshots the user picked).
 */
export function VersionsDiffView({
 before,
 after,
 diff,
 onRollback,
 canRollback = false,
 hideUnchanged = true,
 onToggleHideUnchanged,
}: {
 before: CmsPageVersion;
 after: CmsPageVersion;
 diff: PageVersionDiff;
 onRollback?: (versionId: string) => void;
 canRollback?: boolean;
 hideUnchanged?: boolean;
 onToggleHideUnchanged?: () => void;
}) {
 const visibleSections = hideUnchanged
 ? diff.sections.filter((s) => s.status !== "unchanged")
 : diff.sections;

 return (
 <div className="space-y-4">
 <DiffSummary
 before={before}
 after={after}
 diff={diff}
 onRollback={onRollback}
 canRollback={canRollback}
 hideUnchanged={hideUnchanged}
 onToggleHideUnchanged={onToggleHideUnchanged}
 />
 <PageMetaCard diff={diff} />
 <SectionsCard sections={visibleSections} totalSections={diff.sections.length} />
 </div>
 );
}

// ── Summary header ─────────────────────────────────────────────────────

function DiffSummary({
 before,
 after,
 diff,
 onRollback,
 canRollback,
 hideUnchanged,
 onToggleHideUnchanged,
}: {
 before: CmsPageVersion;
 after: CmsPageVersion;
 diff: PageVersionDiff;
 onRollback?: (versionId: string) => void;
 canRollback?: boolean;
 hideUnchanged: boolean;
 onToggleHideUnchanged?: () => void;
}) {
 const isForward = after.version_number > before.version_number;
 return (
 <motion.section
 initial={{ opacity: 0, y: 6 }}
 animate={{ opacity: 1, y: 0 }}
 className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4"
 >
 <header className="flex flex-wrap items-center justify-between gap-3 mb-4">
 <div className="flex items-center gap-3">
 <div className="size-8 rounded-md bg-info-soft text-[hsl(var(--primary))] flex items-center justify-center">
 <GitCompare size={16} />
 </div>
 <div>
 <h2 className="text-md font-semibold text-[hsl(var(--text-primary))] ">
 Resumen del diff
 </h2>
 <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
 Comparación semántica entre la versión <span className="font-mono">#{before.version_number}</span>{" "}
 y la <span className="font-mono">#{after.version_number}</span>
 {isForward ? "" : " (orden inverso)"}.
 </p>
 </div>
 </div>
 {canRollback && onRollback && (
 <button
 onClick={() => onRollback(before.id)}
 className="inline-flex items-center gap-2 rounded-md border border-[hsl(var(--warning)/30%)] bg-warning-soft px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-warning-text hover:bg-[hsl(var(--warning-muted))] transition-all"
 >
 <ArrowDown size={12} /> Restaurar v{before.version_number}
 </button>
 )}
 </header>
 <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
 <SummaryStat label="Añadidas" value={diff.summary.sectionsAdded} tone="emerald" icon={Plus} />
 <SummaryStat label="Eliminadas" value={diff.summary.sectionsRemoved} tone="rose" icon={Trash2} />
 <SummaryStat label="Reordenadas" value={diff.summary.sectionsReordered} tone="amber" icon={ArrowUp} />
 <SummaryStat label="Modificadas" value={diff.summary.sectionsModified} tone="sky" icon={Edit3} />
 <SummaryStat label="Sin cambios" value={diff.summary.sectionsUnchanged} tone="muted" icon={Minus} />
 <SummaryStat
 label="Campos SEO"
 value={diff.summary.seoFieldsChanged}
 tone={diff.summary.seoFieldsChanged > 0 ? "sky" : "muted"}
 icon={Edit3}
 />
 </div>
 {onToggleHideUnchanged && diff.summary.sectionsUnchanged > 0 && (
 <div className="mt-3 flex items-center justify-end">
 <button
 onClick={onToggleHideUnchanged}
 aria-pressed={hideUnchanged}
 className="inline-flex items-center gap-1.5 rounded-md border border-[hsl(var(--border))] px-2.5 py-1 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-all"
 >
 {hideUnchanged ? "Mostrar secciones sin cambios" : "Ocultar secciones sin cambios"}
 </button>
 </div>
 )}
 </motion.section>
 );
}

function SummaryStat({
 label,
 value,
 tone,
 icon: Icon,
}: {
 label: string;
 value: number;
 tone: "emerald" | "rose" | "amber" | "sky" | "muted";
 icon: LucideIcon;
}) {
 return (
 <div
 className={clsx(
 "rounded-md border px-3 py-2",
 tone === "emerald" && "border-[hsl(var(--success)/25%)] bg-success-soft ",
 tone === "rose" && "border-[hsl(var(--danger)/25%)] bg-danger-soft ",
 tone === "amber" && "border-[hsl(var(--warning)/25%)] bg-warning-soft ",
 tone === "sky" && "border-[hsl(var(--info)/25%)] bg-info-soft ",
 tone === "muted" && "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] ",
 )}
 >
 <div className="flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
 <Icon size={11} /> {label}
 </div>
 <div className="mt-1 text-xl font-bold text-[hsl(var(--text-primary))] ">{value}</div>
 </div>
 );
}

// ── Page metadata ──────────────────────────────────────────────────────

function PageMetaCard({ diff }: { diff: PageVersionDiff }) {
 const any =
 diff.pageMeta.title.kind !== "unchanged" ||
 diff.pageMeta.slug.kind !== "unchanged" ||
 diff.pageMeta.status.kind !== "unchanged" ||
 Object.keys(diff.pageMeta.seo).length > 0;

 if (!any) return null;

 return (
 <section className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-4">
 <header className="flex items-center gap-2">
 <FileText size={14} className="text-[hsl(var(--primary))]" />
 <h3 className="text-sm font-semibold uppercase tracking-wider text-[hsl(var(--text-primary))] ">
 Metadatos de la página
 </h3>
 </header>
 <div className="space-y-3">
 <FieldDiffRow label="Título" diff={diff.pageMeta.title} />
 <FieldDiffRow label="Slug" diff={diff.pageMeta.slug} />
 <FieldDiffRow label="Estado" diff={diff.pageMeta.status} layout="inline" />
 {Object.entries(diff.pageMeta.seo).length > 0 && (
 <div className="space-y-3 pt-3 border-t border-[hsl(var(--border))] ">
 <h4 className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
 SEO
 </h4>
 {Object.entries(diff.pageMeta.seo)
 .sort(([a], [b]) => a.localeCompare(b))
 .map(([key, fieldDiff]) => (
 <FieldDiffRow
 key={key}
 label={humanizeFieldName(key)}
 diff={fieldDiff as FieldDiff}
 multiline={typeof fieldDiff.before === "string" && (fieldDiff.before as string).length > 60}
 />
 ))}
 </div>
 )}
 </div>
 </section>
 );
}

// ── Sections ───────────────────────────────────────────────────────────

function SectionsCard({ sections, totalSections }: { sections: SectionDiffT[]; totalSections: number }) {
 // Stable grouping: kept in their natural order so the reader can
 // scan top-to-bottom. The diff already gives us render order.
 const hidden = totalSections - sections.length;
 return (
 <section className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-3">
 <header className="flex items-center gap-2">
 <GitCompare size={14} className="text-[hsl(var(--primary))]" />
 <h3 className="text-sm font-semibold uppercase tracking-wider text-[hsl(var(--text-primary))] ">
 Secciones ({sections.length}
 {hidden > 0 ? ` de ${totalSections}` : ""})
 </h3>
 {hidden > 0 && (
 <span className="text-2xs text-[hsl(var(--text-secondary))]">
 ({hidden} sin cambios ocultas)
 </span>
 )}
 </header>
 <div className="space-y-2">
 {sections.length === 0 && (
 <div className="rounded-md border border-dashed border-[hsl(var(--border))] p-6 text-center text-sm text-[hsl(var(--text-secondary))]">
 Ninguna de las dos versiones contiene secciones.
 </div>
 )}
 {sections.map((section) => (
 <SectionRow key={`${section.section_key}::${section.status}`} section={section} />
 ))}
 </div>
 </section>
 );
}

function SectionRow({ section }: { section: SectionDiffT }) {
 const tone = sectionTone(section.status);
 const Icon = sectionIcon(section.status);
 return (
 <article
 className={clsx(
 "rounded-md border px-3 py-2.5 transition-all",
 tone.container,
 )}
 >
 <header className="flex flex-wrap items-center justify-between gap-2">
 <div className="flex items-center gap-2 min-w-0">
 <span
 className={clsx(
 "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide",
 tone.badge,
 )}
 >
 <Icon size={10} /> {sectionStatusLabel(section.status)}
 </span>
 <span className="font-mono text-xs text-[hsl(var(--text-secondary))] truncate">
 {section.section_key}
 </span>
 <span className="text-2xs text-[hsl(var(--text-secondary))]">
 · {section.type}
 </span>
 </div>
 {(section.status === "reordered" || section.status === "visibility-changed" || section.status === "status-changed") && (
 <span className="text-2xs text-[hsl(var(--text-secondary))]">
 {section.status === "reordered" && section.sort_before !== undefined && section.sort_after !== undefined && (
 <span className="inline-flex items-center gap-1">
 orden #{section.sort_before}
 <ArrowRight size={10} /> #{section.sort_after}
 </span>
 )}
 {section.status === "visibility-changed" && (
 <span className="inline-flex items-center gap-1">
 <EyeOff size={10} />→<Eye size={10} />
 </span>
 )}
 {section.status === "status-changed" && (
 <span className="inline-flex items-center gap-1">
 {section.before?.status} → {section.after?.status}
 </span>
 )}
 </span>
 )}
 </header>

 {section.status === "added" && section.after && (
 <div className="mt-2.5">
 <SectionPreview
 side="after"
 sectionType={section.type}
 props={section.after.props_json}
 />
 </div>
 )}
 {section.status === "removed" && section.before && (
 <div className="mt-2.5">
 <SectionPreview
 side="before"
 sectionType={section.type}
 props={section.before.props_json}
 />
 </div>
 )}
 {section.status === "unchanged" && section.after && (
 <div className="mt-2.5">
 <SectionPreview
 side="after"
 sectionType={section.type}
 props={section.after.props_json}
 dimmed
 />
 </div>
 )}
 {section.status === "modified" && section.prop_diffs && (
 <div className="mt-2.5 space-y-2.5">
 {filterSemanticPropDiffs(section.type, section.prop_diffs).map(({ key, diff }) => (
 <FieldDiffRow
 key={key}
 label={humanizeFieldName(key)}
 diff={diff}
 multiline={
 typeof diff.before === "string" && (diff.before as string).length > 60
 }
 />
 ))}
 </div>
 )}
 </article>
 );
}

function sectionStatusLabel(status: SectionDiffT["status"]): string {
 switch (status) {
 case "added":
 return "Añadida";
 case "removed":
 return "Eliminada";
 case "reordered":
 return "Reordenada";
 case "visibility-changed":
 return "Visibilidad";
 case "status-changed":
 return "Archivado/Activo";
 case "modified":
 return "Modificada";
 case "unchanged":
 default:
 return "Sin cambios";
 }
}

function sectionIcon(status: SectionDiffT["status"]): LucideIcon {
 switch (status) {
 case "added":
 return Plus;
 case "removed":
 return Trash2;
 case "reordered":
 return ArrowUp;
 case "visibility-changed":
 return EyeOff;
 case "status-changed":
 return Check;
 case "modified":
 return Edit3;
 case "unchanged":
 default:
 return Minus;
 }
}

function sectionTone(status: SectionDiffT["status"]) {
 switch (status) {
 case "added":
 return {
 container: "border-[hsl(var(--success)/25%)] bg-success-soft/40 ",
 badge: "bg-[hsl(var(--success-muted))] text-success-text ",
 };
 case "removed":
 return {
 container: "border-[hsl(var(--danger)/25%)] bg-danger-soft/40 ",
 badge: "bg-[hsl(var(--danger-muted))] text-danger-text ",
 };
 case "reordered":
 return {
 container: "border-[hsl(var(--warning)/25%)] bg-warning-soft/40 ",
 badge: "bg-[hsl(var(--warning-muted))] text-warning-text ",
 };
 case "modified":
 return {
 container: "border-[hsl(var(--info)/25%)] bg-info-soft/40 ",
 badge: "bg-[hsl(var(--info-muted))] text-info-text ",
 };
 case "visibility-changed":
 case "status-changed":
 return {
 container: "border-[hsl(var(--domain-fuchsia)/30%)] bg-[hsl(var(--domain-fuchsia)/40%)] ",
 badge: "bg-[hsl(var(--domain-fuchsia)/20%)] text-[hsl(var(--domain-fuchsia)/90%)] ",
 };
 case "unchanged":
 default:
 return {
 container: "border-[hsl(var(--border))] bg-transparent",
 badge: "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]",
 };
 }
}

/**
 * Render a small preview of a single-side section (used for "added",
 * "removed", and dimmed "unchanged" cards). Picks the section's most
 * informative fields so the reader can scan without opening the
 * builder.
 */
function SectionPreview({
 side,
 sectionType,
 props,
 dimmed = false,
}: {
 side: "before" | "after";
 sectionType: string;
 props?: Record<string, unknown>;
 dimmed?: boolean;
}) {
 if (!props) {
 return (
 <p className="text-xs text-[hsl(var(--text-secondary))] italic">
 (sin props_json)
 </p>
 );
 }
 const title = pickStr(props, ["title", "name", "eyebrow"]);
 const body = pickStr(props, ["body", "description", "caption", "subtitle"]);
 const image = pickStr(props, ["image_url", "image", "cover_url"]);
 const ctaLabel = pickStr(props, ["cta_label", "button_label"]);
 const ctaHref = pickStr(props, ["cta_href", "button_href"]);
 const items = Array.isArray(props.items) ? (props.items as unknown[]) : null;

 return (
 <div
 className={clsx(
 "rounded-md border bg-[hsl(var(--bg-primary))] p-2.5 space-y-1.5",
 side === "before"
 ? "border-[hsl(var(--danger)/25%)]/70 "
 : "border-[hsl(var(--success)/25%)]/70 ",
 dimmed && "opacity-60",
 )}
 >
 {title && (
 <p
 className={clsx(
 "text-sm font-semibold text-[hsl(var(--text-primary))] ",
 side === "before" && "line-through",
 )}
 >
 {title}
 </p>
 )}
 {body && (
 <p
 className={clsx(
 "text-xs text-[hsl(var(--text-secondary))] whitespace-pre-wrap break-words line-clamp-3",
 side === "before" && "line-through",
 )}
 >
 {body}
 </p>
 )}
 {image && (
 <p className="text-2xs font-mono text-[hsl(var(--text-secondary))] truncate">
 🖼 {image}
 </p>
 )}
 {(ctaLabel || ctaHref) && (
 <p className="text-2xs text-[hsl(var(--text-secondary))]">
 {ctaLabel && <span className="font-semibold">[{ctaLabel}]</span>} {ctaHref}
 </p>
 )}
 {items && (
 <div className="text-2xs text-[hsl(var(--text-secondary))]">
 {items.length} ítem{items.length === 1 ? "" : "es"} en ``items``
 </div>
 )}
 <p className="text-2xs uppercase tracking-wider text-[hsl(var(--text-secondary))] opacity-70">
 type: {sectionType}
 </p>
 </div>
 );
}

function pickStr(obj: Record<string, unknown>, keys: string[]): string | null {
 for (const key of keys) {
 const v = obj[key];
 if (typeof v === "string" && v.trim().length > 0) return v;
 }
 return null;
}
