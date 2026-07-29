"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  CivicFileDownloadsProps,
  CivicDataTableProps,
  CivicAlertBannerProps,
} from "@/types/cms-section-props";
import { ChevronRight, Download, X } from "lucide-react";
import React, { useState } from "react";
import { asItems, asProps, val } from "./shared";

export function CivicFileDownloadsSection({ section }: { section: CmsSection<"civic_file_downloads"> }) {
  const props: CivicFileDownloadsProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Documentos para descarga");
  const body = val(p, "body", "");
  const items = asItems(p) as Array<{
    name?: string; file_url?: string; format?: string;
    size_label?: string; description?: string;
  }>;

  const fmtBadge: Record<string, React.ReactNode> = {
    pdf:  <span className="text-2xs font-black text-[hsl(var(--destructive))] bg-[hsl(var(--destructive)/0.08)] border border-[hsl(var(--destructive)/0.2)] px-1.5 py-0.5 rounded select-none">PDF</span>,
    xls:  <span className="text-2xs font-black text-[hsl(var(--success))] bg-[hsl(var(--success-muted))] border border-[hsl(var(--success)/0.2)] px-1.5 py-0.5 rounded select-none">XLS</span>,
    xlsx: <span className="text-2xs font-black text-[hsl(var(--success))] bg-[hsl(var(--success-muted))] border border-[hsl(var(--success)/0.2)] px-1.5 py-0.5 rounded select-none">XLS</span>,
    doc:  <span className="text-2xs font-black text-[hsl(var(--info))] bg-[hsl(var(--info-muted))] border border-[hsl(var(--info)/0.2)] px-1.5 py-0.5 rounded select-none">DOC</span>,
    docx: <span className="text-2xs font-black text-[hsl(var(--info))] bg-[hsl(var(--info-muted))] border border-[hsl(var(--info)/0.2)] px-1.5 py-0.5 rounded select-none">DOC</span>,
    csv:  <span className="text-2xs font-black text-[hsl(var(--success))] bg-[hsl(var(--success-muted))] border border-[hsl(var(--success)/0.2)] px-1.5 py-0.5 rounded select-none">CSV</span>,
    ppt:  <span className="text-2xs font-black text-[hsl(var(--warning))] bg-[hsl(var(--warning-muted))] border border-[hsl(var(--warning)/0.2)] px-1.5 py-0.5 rounded select-none">PPT</span>,
    pptx: <span className="text-2xs font-black text-[hsl(var(--warning))] bg-[hsl(var(--warning-muted))] border border-[hsl(var(--warning)/0.2)] px-1.5 py-0.5 rounded select-none">PPT</span>,
    zip:  <span className="text-2xs font-black text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] px-1.5 py-0.5 rounded select-none">ZIP</span>,
  };

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-2" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {body && <p className="mb-6 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
      <div className="divide-y rounded-xl overflow-hidden border" style={{ borderColor: "var(--site-outline-variant)" }}>
        {items.length === 0 && (
          <div className="flex items-center justify-center py-12 text-sm" style={{ color: "var(--site-on-surface-variant)", background: "var(--site-surface-container)" }}>
            Sin documentos configurados.
          </div>
        )}
        {items.map((item, i) => {
          const fmt = (item.format || "").toLowerCase();
          const badge = fmtBadge[fmt] ?? <span className="text-2xs font-black text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] px-1.5 py-0.5 rounded select-none">FILE</span>;
          return (
            <div key={i} className="flex items-center gap-4 px-5 py-4" style={{ background: i % 2 === 0 ? "var(--site-surface)" : "var(--site-surface-container)" }}>
              <div className="shrink-0">{badge}</div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm truncate" style={{ color: "var(--site-on-surface)" }}>{item.name || `Documento ${i + 1}`}</p>
                {item.description && <p className="text-xs mt-0.5 truncate" style={{ color: "var(--site-on-surface-variant)" }}>{item.description}</p>}
              </div>
              {item.size_label && (
                <span className="text-xs shrink-0" style={{ color: "var(--site-on-surface-variant)" }}>{item.size_label}</span>
              )}
              {item.file_url ? (
                <a
                  href={item.file_url}
                  download
                  className="shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all hover:scale-105 focus-visible:ring-2 focus-visible:ring-offset-2"
                  style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                  aria-label={`Descargar ${item.name || `documento ${i + 1}`}`}
                >
                  <Download size={13} /> Descargar
                </a>
              ) : (
                <span className="text-xs shrink-0 opacity-40" style={{ color: "var(--site-on-surface-variant)" }}>Sin enlace</span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ─── Civic: Accessible Data Table ────────────────────────────────────────────

export function CivicDataTableSection({ section }: { section: CmsSection<"civic_data_table"> }) {
  const props: CivicDataTableProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const caption = val(p, "caption", "");
  const headers = Array.isArray(p.headers) ? (p.headers as string[]) : [];
  const rows = Array.isArray(p.rows) ? (p.rows as string[][]) : [];
  const highlightFirstCol = p.highlight_first_col !== false;
  const striped = p.striped !== false;
  const footerNote = val(p, "footer_note", "");

  return (
    <section
      className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12"
      aria-labelledby={title ? `tbl-title-${section.id}` : undefined}
    >
      {title && (
        <h2 id={`tbl-title-${section.id}`} className="text-xl md:text-2xl font-black tracking-tight mb-4" style={{ color: "var(--site-on-surface)" }}>{title}</h2>
      )}
      <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--site-outline-variant)" }}>
        <table className="w-full text-sm border-collapse" role="table">
          {caption && (
            <caption className="text-xs text-left py-2 px-4 font-medium caption-top" style={{ color: "var(--site-on-surface-variant)" }}>
              {caption}
            </caption>
          )}
          {headers.length > 0 && (
            <thead>
              <tr style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}>
                {headers.map((h, i) => (
                  <th key={i} scope="col" className="px-4 py-3 text-left font-bold text-xs uppercase tracking-wide whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={Math.max(headers.length, 1)} className="px-4 py-10 text-center text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
                  Sin datos configurados.
                </td>
              </tr>
            ) : rows.map((row, ri) => (
              <tr key={ri} style={{ background: striped && ri % 2 === 1 ? "var(--site-surface-container)" : "var(--site-surface)" }}>
                {row.map((cell, ci) =>
                  ci === 0 && highlightFirstCol ? (
                    <th key={ci} scope="row" className="px-4 py-3 font-semibold text-left whitespace-nowrap" style={{ color: "var(--site-on-surface)", borderTop: "1px solid var(--site-outline-variant)" }}>{cell}</th>
                  ) : (
                    <td key={ci} className="px-4 py-3 tabular-nums" style={{ color: "var(--site-on-surface)", borderTop: "1px solid var(--site-outline-variant)" }}>{cell}</td>
                  )
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {footerNote && (
        <p className="mt-3 text-xs" style={{ color: "var(--site-on-surface-variant)" }}>* {footerNote}</p>
      )}
    </section>
  );
}

// ─── Civic: Alert / Emergency Banner ─────────────────────────────────────────

export function CivicAlertBannerSection({ section }: { section: CmsSection<"civic_alert_banner"> }) {
  const props: CivicAlertBannerProps = section.props_json ?? {};
  const p = asProps(props);
  const level = val(p, "level", "warning");
  const title = val(p, "title", "");
  const message = val(p, "message", "");
  const ctaLabel = val(p, "cta_label", "");
  const ctaHref = val(p, "cta_href", "");
  const dismissible = p.dismissible !== false;
  const [dismissed, setDismissed] = useState(false);

  const levels: Record<string, { bg: string; border: string; accent: string; icon: string; text: string }> = {
    info:    { bg: "hsl(var(--info-muted))", border: "hsl(var(--info)/0.3)", accent: "hsl(var(--info))", icon: "ℹ️", text: "hsl(var(--info))" },
    warning: { bg: "hsl(var(--warning-muted))", border: "hsl(var(--warning)/0.3)", accent: "hsl(var(--warning))", icon: "⚠️", text: "hsl(var(--warning))" },
    danger:  { bg: "hsl(var(--destructive)/0.08)", border: "hsl(var(--destructive)/0.2)", accent: "hsl(var(--destructive))", icon: "🚨", text: "hsl(var(--destructive))" },
  };
  const s = levels[level] || levels.warning;

  if (dismissed) return null;

  return (
    <div role="alert" aria-live="assertive" className="w-full border rounded-xl" style={{ background: s.bg, borderColor: s.border, borderLeftWidth: 4, borderLeftColor: s.accent }}>
      <div className="flex items-start gap-3 px-5 py-4">
        <span className="text-xl shrink-0 mt-0.5" aria-hidden="true">{s.icon}</span>
        <div className="flex-1 min-w-0">
          {title && <p className="font-black text-base mb-1" style={{ color: s.text }}>{title}</p>}
          {message && <p className="text-sm leading-relaxed" style={{ color: s.text }}>{message}</p>}
          {ctaHref && ctaLabel && (
            <a href={ctaHref} className="inline-flex items-center gap-1 mt-3 text-xs font-bold underline underline-offset-2" style={{ color: s.accent }}>
              {ctaLabel} <ChevronRight size={12} />
            </a>
          )}
        </div>
        {dismissible && (
          <button
            type="button"
            onClick={() => setDismissed(true)}
            className="shrink-0 p-1 rounded-full opacity-60 hover:opacity-100 transition-opacity"
            aria-label="Cerrar alerta"
          >
            <X size={16} style={{ color: s.accent }} />
          </button>
        )}
      </div>
    </div>
  );
}
