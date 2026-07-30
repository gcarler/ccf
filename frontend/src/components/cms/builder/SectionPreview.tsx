import React from "react";
import type { CmsSection } from "@/types/cms-v2";
import type { CanvasMode, PageBuilderState } from "@/hooks/usePageBuilder";
import { updateCmsSectionProps } from "@/lib/cms/v2";
import { toast } from "sonner";
import { Check, X } from "lucide-react";
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

export class SectionRenderErrorBoundary extends React.Component<
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

// ── Quick Floating Inline Editor Panel ──────────────────────────────────────

interface InlineEditorPanelProps {
  section: CmsSection;
  builder: PageBuilderState;
  onClose: () => void;
}

export function InlineEditorPanel({ section, builder, onClose }: InlineEditorPanelProps) {
  const [propsJson, setPropsJson] = React.useState<Record<string, any>>(() => ({
    ...(section.props_json || {}),
  }));
  const [saveStatus, setSaveStatus] = React.useState<string | null>(null);
  const debounceTimerRef = React.useRef<NodeJS.Timeout | null>(null);

  React.useEffect(() => {
    setPropsJson({ ...(section.props_json || {}) });
  }, [section.props_json]);

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (debounceTimerRef.current) {
          clearTimeout(debounceTimerRef.current);
        }
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  React.useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const handleFieldChange = (key: string, value: string) => {
    const nextProps = { ...propsJson, [key]: value };

    if (key === "headline") nextProps.title = value;
    if (key === "title" && section.type === "cta_banner") nextProps.headline = value;
    if (key === "subtext") {
      nextProps.subtitle = value;
      nextProps.body = value;
    }
    if (key === "subtitle") {
      nextProps.subtext = value;
      nextProps.body = value;
    }
    if (key === "cta_text") nextProps.cta_label = value;
    if (key === "cta_label") nextProps.cta_text = value;
    if (key === "cta_url") nextProps.cta_href = value;
    if (key === "cta_href") nextProps.cta_url = value;

    setPropsJson(nextProps);
    setSaveStatus("Guardando...");

    if (builder.updateSectionPropsLocal) {
      builder.updateSectionPropsLocal(nextProps, section.id);
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(async () => {
      try {
        if (builder.siteKey && builder.activeSlug) {
          await updateCmsSectionProps(
            builder.siteKey,
            builder.activeSlug,
            section.id,
            nextProps,
            builder.token
          );
          setSaveStatus("✓ Guardado");
        } else {
          setSaveStatus("✓ Guardado");
        }
      } catch (err) {
        toast.error("No se pudo guardar los cambios");
        setSaveStatus(null);
      }
    }, 800);
  };

  const handleSaveImmediate = async () => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    setSaveStatus("Guardando...");
    try {
      if (builder.siteKey && builder.activeSlug) {
        await updateCmsSectionProps(
          builder.siteKey,
          builder.activeSlug,
          section.id,
          propsJson,
          builder.token
        );
      }
      setSaveStatus("✓ Guardado");
      onClose();
    } catch (err) {
      toast.error("No se pudo guardar los cambios");
      setSaveStatus(null);
    }
  };

  const fields = React.useMemo(() => {
    const type = section.type;
    switch (type) {
      case "hero":
      case "video_hero":
        return [
          { key: "title", label: "Título", type: "input", value: safeString(propsJson.title) },
          { key: "subtitle", label: "Subtítulo", type: "input", value: safeString(propsJson.subtitle || propsJson.body) },
          { key: "cta_text", label: "Texto CTA", type: "input", value: safeString(propsJson.cta_text || propsJson.cta_label) },
          { key: "cta_url", label: "URL CTA", type: "input", value: safeString(propsJson.cta_url || propsJson.cta_href) },
        ];
      case "cards":
      case "pricing":
        return [
          { key: "title", label: "Título", type: "input", value: safeString(propsJson.title) },
          { key: "subtitle", label: "Subtítulo", type: "input", value: safeString(propsJson.subtitle || propsJson.body) },
        ];
      case "rich_text":
      case "rich_text_columns":
        return [
          { key: "title", label: "Título", type: "input", value: safeString(propsJson.title) },
          { key: "body", label: "Contenido", type: "textarea", value: safeString(propsJson.body) },
        ];
      case "cta_banner":
        return [
          { key: "headline", label: "Titular", type: "input", value: safeString(propsJson.headline || propsJson.title) },
          { key: "subtext", label: "Subtexto", type: "input", value: safeString(propsJson.subtext || propsJson.subtitle || propsJson.body) },
          { key: "cta_text", label: "Texto CTA", type: "input", value: safeString(propsJson.cta_text || propsJson.cta_label) },
          { key: "cta_url", label: "URL CTA", type: "input", value: safeString(propsJson.cta_url || propsJson.cta_href) },
        ];
      case "stats":
        return [
          { key: "title", label: "Título", type: "input", value: safeString(propsJson.title) },
        ];
      case "team":
        return [
          { key: "title", label: "Título", type: "input", value: safeString(propsJson.title) },
          { key: "subtitle", label: "Subtítulo", type: "input", value: safeString(propsJson.subtitle || propsJson.body) },
        ];
      case "testimonials":
        return [
          { key: "title", label: "Título", type: "input", value: safeString(propsJson.title) },
        ];
      case "faq":
        return [
          { key: "title", label: "Título", type: "input", value: safeString(propsJson.title) },
        ];
      default: {
        const res = [];
        res.push({ key: "title", label: "Título", type: "input", value: safeString(propsJson.title) });
        if ("subtitle" in propsJson || "body" in propsJson || "subtext" in propsJson) {
          res.push({ key: "subtitle", label: "Subtítulo", type: "input", value: safeString(propsJson.subtitle || propsJson.subtext || propsJson.body) });
        }
        return res;
      }
    }
  }, [section.type, propsJson]);

  return (
    <div
      className="absolute inset-0 z-40 p-4 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm shadow-xl rounded-lg border-2 border-primary overflow-y-auto flex flex-col justify-between"
      onClick={(e) => e.stopPropagation()}
    >
      <div>
        <div className="flex items-center justify-between gap-2 border-b border-[hsl(var(--border))] dark:border-white/10 pb-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-2xs font-bold uppercase bg-primary/20 text-primary">
              Inline Editor · {section.type}
            </span>
            {saveStatus && (
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  saveStatus.includes("Guardado")
                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                    : "bg-amber-500/10 text-amber-600 dark:text-amber-400 animate-pulse"
                }`}
              >
                {saveStatus}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSaveImmediate}
              className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold transition-colors"
              title="Guardar cambios"
            >
              <Check size={13} /> ✓ Guardar
            </button>
            <button
              type="button"
              onClick={() => {
                if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
                onClose();
              }}
              className="inline-flex items-center gap-1 px-2 py-1 bg-gray-200 dark:bg-gray-800 hover:bg-gray-300 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 rounded text-xs font-semibold transition-colors"
              title="Cerrar sin guardar"
            >
              <X size={13} /> ✕ Cerrar
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {fields.map((f) => (
            <div key={f.key} className="space-y-1 text-left">
              <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                {f.label}
              </label>
              {f.type === "textarea" ? (
                <textarea
                  value={f.value}
                  onChange={(e) => handleFieldChange(f.key, e.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-[hsl(var(--border))] dark:border-white/20 bg-background dark:bg-gray-950 px-3 py-1.5 text-xs text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                />
              ) : (
                <input
                  type="text"
                  value={f.value}
                  onChange={(e) => handleFieldChange(f.key, e.target.value)}
                  className="w-full rounded-md border border-[hsl(var(--border))] dark:border-white/20 bg-background dark:bg-gray-950 px-3 py-1.5 text-xs text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                />
              )}
            </div>
          ))}
        </div>
      </div>
      <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-3 text-right">
        Presiona Esc para cerrar el editor inline.
      </p>
    </div>
  );
}

// ── Full render preview (uses PublicSectionRenderer) ────────────────────────

export function SectionRenderPreview({
  section,
  mobile,
  tokens,
  canvasMode,
  builder,
}: {
  section: CmsSection;
  mobile: boolean;
  tokens?: React.CSSProperties;
  canvasMode?: CanvasMode;
  builder?: PageBuilderState;
}) {
  const [inlineEditing, setInlineEditing] = React.useState(false);

  const handleDoubleClick = (e: React.MouseEvent) => {
    if (canvasMode === "wysiwyg") {
      e.stopPropagation();
      setInlineEditing(true);
    }
  };

  return (
    <div
      data-testid="section-render-preview"
      style={tokens ?? CANVAS_PREVIEW_TOKENS}
      className={`relative rounded-lg overflow-hidden border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))]${
        mobile ? " max-w-[420px] mx-auto" : ""
      }`}
      onDoubleClick={handleDoubleClick}
    >
      <SectionRenderErrorBoundary>
        <PublicSectionRenderer section={section} />
      </SectionRenderErrorBoundary>

      {canvasMode === "wysiwyg" && inlineEditing && builder && (
        <InlineEditorPanel
          section={section}
          builder={builder}
          onClose={() => setInlineEditing(false)}
        />
      )}
    </div>
  );
}

// ── Type badge used across all section preview variants ─────────────────────

function TypeBadge({ type }: { type: string }) {
  const typeLabel = SECTION_TYPE_LABEL[type] ?? type;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-md text-2xs font-semibold uppercase tracking-wide"
      style={{ backgroundColor: 'var(--site-primary)', color: 'var(--site-on-primary)' }}
    >
      {typeLabel}
    </span>
  );
}

// ── Schema preview (shows a type-specific placeholder) ──────────────────────

export function SectionPreview({ section }: { section: CmsSection }) {
  const title = safeString(section.props_json?.title);
  const body = safeString(section.props_json?.body);
  const imageUrl = safeString(section.props_json?.image_url);
  const ctaLabel = safeString(section.props_json?.cta_label);
  const typeBadge = <TypeBadge type={section.type} />;

  if (section.type === "hero" || section.type === "video_hero") {
    return (
      <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/20 p-4 space-y-2">
        {typeBadge}
        <h3 className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white leading-tight">
          {title || "Título hero"}
        </h3>
        <p className="text-sm text-[hsl(var(--text-secondary))] line-clamp-2">{body || "Subtítulo o descripción principal"}</p>
        {ctaLabel && (
          <span className="inline-block mt-1 px-3 py-1 bg-[hsl(var(--primary))] text-white rounded-lg text-2xs font-semibold uppercase">
            {ctaLabel}
          </span>
        )}
        {section.type === "video_hero" && (
          <p className="text-2xs text-[hsl(var(--text-secondary))] font-bold uppercase">🎬 Video de fondo configurado</p>
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
        {typeBadge}
        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
          {title || "Bloque de tarjetas"}
        </p>
        {items.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {items.slice(0, 3).map((item, idx) => (
              <span
                key={idx}
                className="px-2 py-1 bg-[hsl(var(--surface-2))] dark:bg-white/10 rounded-lg text-2xs font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
              >
                {safeString(item.title) || `Item ${idx + 1}`}
              </span>
            ))}
            {items.length > 3 && (
              <span className="text-2xs text-[hsl(var(--text-secondary))]">
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
        {typeBadge}
        {imageUrl ? (
          <OptimizedImage
            src={imageUrl}
            alt="gallery"
            width={200}
            height={96}
            className="w-full h-24 object-cover rounded-md"
          />
        ) : (
          <div className="w-full h-8 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-2xs text-[hsl(var(--text-secondary))] font-bold uppercase">
            Sin imagen configurada
          </div>
        )}
      </div>
    );
  }
  if (section.type === "cta_banner") {
    return (
      <div className="rounded-lg border border-dashed p-4 space-y-2" style={{ borderColor: 'var(--site-primary)', backgroundColor: 'var(--site-primary-container)' }}>
        {typeBadge}
        <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
          {title || "Llamado a la Acción"}
        </p>
        <p className="text-xs text-[hsl(var(--text-secondary))] line-clamp-1">{body || "Subtítulo"}</p>
        {ctaLabel && (
          <span className="inline-block px-3 py-1 text-white rounded-lg text-2xs font-semibold uppercase" style={{ backgroundColor: 'var(--site-primary)' }}>
            {ctaLabel}
          </span>
        )}
      </div>
    );
  }
  if (section.type === "testimonials") {
    return (
      <div className="rounded-lg border border-dashed p-4 space-y-2" style={{ borderColor: 'var(--site-outline-variant)' }}>
        {typeBadge}
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
        {typeBadge}
        <div className="grid grid-cols-3 gap-2">
          {(stats.length > 0 ? stats : [{ value: "—", label: "Métrica" }])
            .slice(0, 3)
            .map((s, i) => (
              <div key={i} className="text-center">
                <p className="text-base font-semibold" style={{ color: 'var(--site-primary)' }}>
                  {safeString(s.value) || "—"}
                </p>
                <p className="text-2xs text-[hsl(var(--text-secondary))] font-bold uppercase">
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
        {typeBadge}
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
        {typeBadge}
        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
          {title || "Cuenta Regresiva"}
        </p>
        <div className="flex gap-3">
          {["DD", "HH", "MM", "SS"].map((u) => (
            <div key={u} className="text-center">
              <div className="size-10 rounded-md bg-[hsl(var(--destructive))] flex items-center justify-center text-white font-semibold text-sm">
                00
              </div>
              <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5 font-bold uppercase">
                {u}
              </p>
            </div>
          ))}
        </div>
        {target && (
          <p className="text-2xs text-[hsl(var(--text-secondary))]">Hasta: {target}</p>
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
        {typeBadge}
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
        {typeBadge}
        {embedUrl ? (
          <p className="text-2xs text-[hsl(var(--text-secondary))] font-mono truncate">
            {embedUrl}
          </p>
        ) : (
          <div className="w-full h-8 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-2xs text-[hsl(var(--text-secondary))] font-bold uppercase">
            Sin URL configurada
          </div>
        )}
      </div>
    );
  }
  // rich_text, rich_text_columns, and default fallback
  return (
    <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/20 p-4 space-y-2">
      <TypeBadge type={section.type} />
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
