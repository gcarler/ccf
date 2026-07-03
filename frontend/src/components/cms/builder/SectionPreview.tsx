import React from "react";
import type { CmsSection } from "@/types/cms-v2";
import OptimizedImage from "@/components/ui/OptimizedImage";
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";
import {
  SECTION_TYPE_LABEL,
} from "@/components/cms/builder/constants";
import {
  safeString,
  CANVAS_PREVIEW_TOKENS,
} from "@/components/cms/builder/utils";

// ── Render error boundary ───────────────────────────────────────────────────

class SectionRenderErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: false };
  }
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    if (this.state.error) {
      return (
        <div className="rounded-lg border border-dashed border-red-300 bg-red-50/40 p-4 text-center text-xs font-semibold text-[hsl(var(--destructive))]">
          No se pudo renderizar esta sección.
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Full render preview (uses PublicSectionRenderer) ────────────────────────

export function SectionRenderPreview({
  section,
  mobile,
  tokens,
}: {
  section: CmsSection;
  mobile: boolean;
  tokens?: React.CSSProperties;
}) {
  return (
    <div
      style={tokens ?? CANVAS_PREVIEW_TOKENS}
      className={`rounded-lg overflow-hidden border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))]${mobile ? " max-w-[420px] mx-auto" : ""}`}
    >
      <SectionRenderErrorBoundary>
        <PublicSectionRenderer section={section} />
      </SectionRenderErrorBoundary>
    </div>
  );
}

// ── Schema preview (shows a type-specific placeholder) ──────────────────────

export function SectionPreview({ section }: { section: CmsSection }) {
  const title = safeString(section.props_json?.title);
  const body = safeString(section.props_json?.body);
  const imageUrl = safeString(section.props_json?.image_url);
  const ctaLabel = safeString(section.props_json?.cta_label);
  const typeLabel = SECTION_TYPE_LABEL[section.type] ?? section.type;

  const TypeBadge = () => (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-semibold uppercase tracking-wide"
      style={{ backgroundColor: 'var(--site-primary)', color: 'var(--site-on-primary)' }}
    >
      {typeLabel}
    </span>
  );

  if (section.type === "hero" || section.type === "video_hero") {
    return (
      <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/20 p-4 space-y-2">
        <TypeBadge />
        <h3 className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white leading-tight">
          {title || "Título hero"}
        </h3>
        <p className="text-sm text-[hsl(var(--text-secondary))] line-clamp-2">{body || "Subtítulo o descripción principal"}</p>
        {ctaLabel && (
          <span className="inline-block mt-1 px-3 py-1 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-semibold uppercase">
            {ctaLabel}
          </span>
        )}
        {section.type === "video_hero" && (
          <p className="text-[9px] text-[hsl(var(--text-secondary))] font-bold uppercase">🎬 Video de fondo configurado</p>
        )}
      </div>
    );
  }
  if (section.type === "cards" || section.type === "pricing") {
    const items = Array.isArray(section.props_json?.items)
      ? (section.props_json.items as Array<Record<string, unknown>>).filter(
          (item) => item.status !== "archived"
        )
      : [];
    return (
      <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/20 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
          {title || "Bloque de tarjetas"}
        </p>
        {items.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {items.slice(0, 3).map((item, idx) => (
              <span
                key={idx}
                className="px-2 py-1 bg-[hsl(var(--surface-2))] dark:bg-white/10 rounded-lg text-[9px] font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
              >
                {safeString(item.title) || `Item ${idx + 1}`}
              </span>
            ))}
            {items.length > 3 && (
              <span className="text-[9px] text-[hsl(var(--text-secondary))]">
                +{items.length - 3} más
              </span>
            )}
          </div>
        )}
      </div>
    );
  }
  if (section.type === "gallery") {
    return (
      <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/20 p-4 space-y-2">
        <TypeBadge />
        {imageUrl ? (
          <OptimizedImage
            src={imageUrl}
            alt="gallery"
            width={200}
            height={96}
            className="w-full h-24 object-cover rounded-md"
          />
        ) : (
          <div className="w-full h-8 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[9px] text-[hsl(var(--text-secondary))] font-bold uppercase">
            Sin imagen configurada
          </div>
        )}
      </div>
    );
  }
  if (section.type === "cta_banner") {
    return (
      <div className="rounded-lg border border-dashed p-4 space-y-2" style={{ borderColor: 'var(--site-primary)', backgroundColor: 'var(--site-primary-container)' }}>
        <TypeBadge />
        <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
          {title || "Llamado a la Acción"}
        </p>
        <p className="text-xs text-[hsl(var(--text-secondary))] line-clamp-1">{body || "Subtítulo"}</p>
        {ctaLabel && (
          <span className="inline-block px-3 py-1 text-white rounded-lg text-[10px] font-semibold uppercase" style={{ backgroundColor: 'var(--site-primary)' }}>
            {ctaLabel}
          </span>
        )}
      </div>
    );
  }
  if (section.type === "testimonials") {
    return (
      <div className="rounded-lg border border-dashed p-4 space-y-2" style={{ borderColor: 'var(--site-outline-variant)' }}>
        <TypeBadge />
        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
          {title || "Sección de Testimonios"}
        </p>
        <div className="flex gap-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex-1 h-8 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }
  if (section.type === "stats") {
    const stats = Array.isArray(section.props_json?.items)
      ? (section.props_json.items as Array<Record<string, unknown>>)
      : [];
    return (
      <div className="rounded-lg border border-dashed p-4 space-y-2" style={{ borderColor: 'var(--site-primary)' }}>
        <TypeBadge />
        <div className="grid grid-cols-3 gap-2">
          {(stats.length > 0 ? stats : [{ value: "—", label: "Métrica" }])
            .slice(0, 3)
            .map((s, i) => (
              <div key={i} className="text-center">
                <p className="text-base font-semibold" style={{ color: 'var(--site-primary)' }}>
                  {safeString(s.value) || "—"}
                </p>
                <p className="text-[9px] text-[hsl(var(--text-secondary))] font-bold uppercase">
                  {safeString(s.label) || "Métrica"}
                </p>
              </div>
            ))}
        </div>
      </div>
    );
  }
  if (section.type === "team") {
    return (
      <div className="rounded-lg border border-dashed p-4 space-y-2" style={{ borderColor: 'var(--site-secondary)' }}>
        <TypeBadge />
        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
          {title || "Nuestro Equipo"}
        </p>
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="size-8 rounded-full border-2 border-white dark:border-[hsl(var(--border))]"
              style={{ backgroundColor: 'color-mix(in srgb, var(--site-secondary) 25%, transparent)' }}
            />
          ))}
        </div>
      </div>
    );
  }
  if (section.type === "countdown") {
    const target = safeString(section.props_json?.target_date);
    return (
      <div className="rounded-lg border border-dashed p-4 space-y-2" style={{ borderColor: 'var(--site-primary)' }}>
        <TypeBadge />
        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
          {title || "Cuenta Regresiva"}
        </p>
        <div className="flex gap-3">
          {["DD", "HH", "MM", "SS"].map((u) => (
            <div key={u} className="text-center">
              <div className="size-10 rounded-md bg-[hsl(var(--destructive))] flex items-center justify-center text-white font-semibold text-sm">
                00
              </div>
              <p className="text-[8px] text-[hsl(var(--text-secondary))] mt-0.5 font-bold uppercase">
                {u}
              </p>
            </div>
          ))}
        </div>
        {target && (
          <p className="text-[9px] text-[hsl(var(--text-secondary))]">Hasta: {target}</p>
        )}
      </div>
    );
  }
  if (section.type === "faq") {
    const faqs = Array.isArray(section.props_json?.items)
      ? (section.props_json.items as Array<Record<string, unknown>>).filter(
          (item) => item.status !== "archived"
        )
      : [];
    return (
      <div className="rounded-lg border border-dashed p-4 space-y-2" style={{ borderColor: 'var(--site-secondary)' }}>
        <TypeBadge />
        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
          {title || "Preguntas Frecuentes"}
        </p>
        {faqs.slice(0, 2).map((f, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className="font-semibold mt-0.5" style={{ color: 'var(--site-secondary)' }}>Q</span>
            <span className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] line-clamp-1">
              {safeString(f.q) || "Pregunta"}
            </span>
          </div>
        ))}
      </div>
    );
  }
  if (section.type === "embed") {
    const embedUrl = safeString(section.props_json?.embed_url);
    return (
      <div className="rounded-lg border border-dashed p-4 space-y-2" style={{ borderColor: 'var(--site-primary)' }}>
        <TypeBadge />
        {embedUrl ? (
          <p className="text-[10px] text-[hsl(var(--text-secondary))] font-mono truncate">
            {embedUrl}
          </p>
        ) : (
          <div className="w-full h-8 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[9px] text-[hsl(var(--text-secondary))] font-bold uppercase">
            Sin URL configurada
          </div>
        )}
      </div>
    );
  }
  // rich_text, rich_text_columns, and default fallback
  return (
    <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/20 p-4 space-y-2">
      <TypeBadge />
      <h4 className="text-base font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
        {title || "Título"}
      </h4>
      <p className="text-sm text-[hsl(var(--text-secondary))] line-clamp-3">
        {body || "Contenido de sección"}
      </p>
      {section.type === "rich_text_columns" && (
        <div className="flex gap-2 mt-1">
          <div className="flex-1 h-2 rounded bg-[hsl(var(--surface-3))] dark:bg-white/10" />
          <div className="flex-1 h-2 rounded bg-[hsl(var(--surface-3))] dark:bg-white/10" />
        </div>
      )}
    </div>
  );
}
