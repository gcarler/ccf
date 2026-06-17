"use client";

import React, { useEffect, useMemo, useState } from "react";
import { SITE_KEY, SITE_URL } from "@/lib/site-config";
import { Archive, ArrowDown, ArrowUp, Check, Copy, Eye, EyeOff, ExternalLink, FileImage, ImageIcon, LayoutPanelTop, Monitor, Plus, RotateCcw, Save, Search, Send, Smartphone, Upload, Undo2, X, Settings, Sparkles, BarChart3, CheckCircle2, AlertTriangle, XCircle, Wand2, RefreshCw } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
  createCmsPage,
  createCmsSection,
  listCmsPageVersions,
  listCmsPagePublishLog,
  listCmsPages,
  listCmsSections,
  listCmsSites,
  patchCmsPage,
  patchCmsSection,
  reorderCmsSections,
  rollbackCmsPageVersion,
  workflowCmsPage,
} from "@/lib/cms/v2";
import { CmsPage, CmsPageVersion, CmsPublishLog, CmsSection } from "@/types/cms-v2";
import { useSearchParams } from "next/navigation";
import { canEditCms, canPublishCms } from "@/lib/cms/permissions";
import { apiFetch } from "@/lib/http";
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";

const SECTION_TYPES = [
  "hero", "video_hero", "rich_text", "rich_text_columns",
  "cards", "cta_banner", "gallery", "faq", "embed",
  "testimonials", "stats", "team", "countdown", "pricing",
  "image_text", "timeline", "icon_grid", "newsletter", "popup_banner",
  // New
  "button", "toc", "divider", "collapsible", "social_links",
  "spacer", "calendar", "map", "document_upload", "content_blocks", "accordion",
  // Civic
  "civic_hero_search", "civic_convocatoria_cards", "civic_quick_links",
  "civic_file_downloads", "civic_data_table", "civic_alert_banner",
];

const SECTION_TYPE_COLORS: Record<string, string> = {
  hero:              "bg-[hsl(var(--primary))]",
  video_hero:        "bg-[hsl(var(--primary))]",
  rich_text:         "bg-slate-500",
  rich_text_columns: "bg-slate-600",
  cards:             "bg-[hsl(var(--primary))]",
  cta_banner:        "bg-emerald-600",
  gallery:           "bg-pink-500",
  faq:               "bg-amber-500",
  embed:             "bg-cyan-600",
  testimonials:      "bg-rose-500",
  stats:             "bg-teal-600",
  team:              "bg-orange-500",
  countdown:         "bg-[hsl(var(--destructive))]",
  pricing:           "bg-sky-600",
  image_text:        "bg-[hsl(var(--primary))]",
  timeline:          "bg-lime-600",
  icon_grid:         "bg-yellow-600",
  newsletter:        "bg-[hsl(var(--primary))]",
  popup_banner:      "bg-fuchsia-500",
  button:            "bg-[hsl(var(--primary))]",
  toc:               "bg-zinc-500",
  divider:           "bg-gray-400",
  collapsible:       "bg-blue-500",
  social_links:      "bg-sky-500",
  spacer:            "bg-stone-400",
  calendar:          "bg-[hsl(var(--primary))]",
  map:               "bg-[hsl(var(--secondary))]",
  document_upload:   "bg-amber-600",
  content_blocks:    "bg-pink-400",
  accordion:              "bg-teal-500",
  civic_hero_search:      "bg-blue-700",
  civic_convocatoria_cards: "bg-emerald-700",
  civic_quick_links:      "bg-sky-600",
  civic_file_downloads:   "bg-rose-600",
  civic_data_table:       "bg-teal-700",
  civic_alert_banner:     "bg-red-600",
};

const SECTION_TYPE_LABEL: Record<string, string> = {
  hero:              "Hero Principal",
  video_hero:        "Hero con Video",
  rich_text:         "Texto Enriquecido",
  rich_text_columns: "Texto 2 Columnas",
  cards:             "Tarjetas",
  cta_banner:        "Banner CTA",
  gallery:           "Galería",
  faq:               "Preguntas Frecuentes",
  embed:             "Embed / iFrame",
  testimonials:      "Testimonios",
  stats:             "Estadísticas",
  team:              "Equipo",
  countdown:         "Cuenta Regresiva",
  pricing:           "Precios / Donaciones",
  image_text:        "Imagen + Texto",
  timeline:          "Línea de Tiempo",
  icon_grid:         "Grid de Iconos",
  newsletter:        "Suscripción Email",
  popup_banner:      "Pop-up Promocional",
  button:            "Botones",
  toc:               "Índice / Tabla de Contenidos",
  divider:           "Divisor / Separador",
  collapsible:       "Grupo Ocultable",
  social_links:      "Redes Sociales",
  spacer:            "Espaciador",
  calendar:          "Calendario",
  map:               "Mapa",
  document_upload:   "Cargar Documentos",
  content_blocks:    "Bloques de Contenido",
  accordion:              "Acordeón",
  civic_hero_search:      "Buscador Hero (Cívico)",
  civic_convocatoria_cards: "Tarjetas Convocatoria",
  civic_quick_links:      "Enlaces Rápidos (Cívico)",
  civic_file_downloads:   "Descargas de Archivos",
  civic_data_table:       "Tabla de Datos Accesible",
  civic_alert_banner:     "Banner de Alerta / Emergencia",
};

interface CmsMediaItem {
  id: number;
  url: string;
  filename?: string | null;
  mime_type?: string | null;
  alt_text?: string | null;
  section?: string;
  tags?: string[];
  created_at?: string;
}

const PAGE_TEMPLATES: Array<{ key: string; label: string; sections: Array<{ type: string; props_json: Record<string, unknown> }> }> = [
  {
    key: "landing",
    label: "Landing completa",
    sections: [
      {
        type: "hero",
        props_json: {
          title: "Bienvenido a nuestra comunidad",
          body: "Una casa para crecer en fe y servir con propósito.",
          cta_label: "Conocer más",
          cta_href: "/nosotros",
        },
      },
      {
        type: "cards",
        props_json: {
          title: "Nuestra ruta",
          body: "Conecta, crece y sirve.",
          items: [
            { title: "Conecta", body: "Únete a una comunidad cercana." },
            { title: "Crece", body: "Profundiza en la Palabra." },
            { title: "Sirve", body: "Impacta tu entorno." },
          ],
        },
      },
      {
        type: "faq",
        props_json: {
          title: "Preguntas frecuentes",
          items: [
            { q: "¿Cómo llegar?", a: "Revisa nuestra sección de sedes." },
            { q: "¿Cómo empezar?", a: "Visítanos y te acompañamos en tu proceso." },
          ],
        },
      },
      {
        type: "cta_banner",
        props_json: {
          title: "Da tu siguiente paso",
          body: "Queremos caminar contigo.",
          cta_label: "Planificar visita",
          cta_href: "/conocer-a-jesus",
        },
      },
    ],
  },
  {
    key: "simple",
    label: "Página simple",
    sections: [
      { type: "rich_text", props_json: { title: "Título", body: "Contenido principal" } },
      { type: "cta_banner", props_json: { title: "Llamado a la acción", body: "Invita al usuario a avanzar", cta_label: "Continuar", cta_href: "/" } },
    ],
  },
];

const SECTION_TEMPLATES: Array<{ label: string; type: string; props_json: Record<string, unknown> }> = [
  {
    label: "Hero principal",
    type: "hero",
    props_json: {
      title: "Una comunidad que transforma vidas",
      body: "Conecta con Jesús, crece en discipulado y sirve con propósito.",
      cta_label: "Planifica tu visita",
      cta_href: "/conocer-a-jesus",
    },
  },
  {
    label: "Bloque de tarjetas",
    type: "cards",
    props_json: {
      title: "Nuestra ruta de crecimiento",
      body: "Explora los pasos clave de formación y servicio.",
      items: [
        { title: "Conecta", body: "Conoce la casa y encuentra comunidad." },
        { title: "Crece", body: "Fortalece tu fe con formación continua." },
        { title: "Sirve", body: "Activa tus dones para impactar la ciudad." },
      ],
    },
  },
  {
    label: "Banner CTA",
    type: "cta_banner",
    props_json: {
      title: "¿Listo para dar el siguiente paso?",
      body: "Conoce nuestros próximos eventos y grupos de la iglesia.",
      cta_label: "Ver eventos",
      cta_href: "/eventos",
    },
  },
  {
    label: "FAQ rápido",
    type: "faq",
    props_json: {
      title: "Preguntas frecuentes",
      body: "Resuelve dudas comunes antes de visitarnos.",
      items: [
        { q: "¿Dónde están ubicados?", a: "Puedes ver todas nuestras sedes en la sección de Sedes." },
        { q: "¿Cómo puedo empezar?", a: "Comienza visitándonos o escribiéndonos desde Conocer a Jesús." },
      ],
    },
  },
];

function safeString(value: unknown) {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function asObject(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as Record<string, unknown>;
  return {};
}

const CANVAS_PREVIEW_TOKENS: React.CSSProperties = {
  "--site-background": "#f8f9ff",
  "--site-on-background": "#101828",
  "--site-surface": "#ffffff",
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
  "--site-cta-gradient": "linear-gradient(135deg,#3155d4,#1a3ab8)",
  "--site-outline-variant": "rgba(0,0,0,0.1)",
} as React.CSSProperties;

class SectionRenderErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: false };
  }
  static getDerivedStateFromError() { return { error: true }; }
  render() {
    if (this.state.error) {
      return (
        <div className="rounded-lg border border-dashed border-red-300 bg-red-50/40 p-4 text-center text-xs font-semibold text-red-500">
          No se pudo renderizar esta sección.
        </div>
      );
    }
    return this.props.children;
  }
}

function SectionRenderPreview({ section, mobile }: { section: CmsSection; mobile: boolean }) {
  return (
    <div
      style={CANVAS_PREVIEW_TOKENS}
      className={`rounded-lg overflow-hidden border border-slate-200 dark:border-white/10 bg-white${mobile ? " max-w-[420px] mx-auto" : ""}`}
    >
      <SectionRenderErrorBoundary>
        <PublicSectionRenderer section={section} />
      </SectionRenderErrorBoundary>
    </div>
  );
}

function SectionPreview({ section }: { section: CmsSection }) {
  const title = safeString(section.props_json?.title);
  const body = safeString(section.props_json?.body);
  const imageUrl = safeString(section.props_json?.image_url);
  const ctaLabel = safeString(section.props_json?.cta_label);
  const typeColor = SECTION_TYPE_COLORS[section.type] ?? "bg-slate-500";
  const typeLabel = SECTION_TYPE_LABEL[section.type] ?? section.type;

  const TypeBadge = () => (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-semibold uppercase tracking-wide text-white ${typeColor}`}>
      {typeLabel}
    </span>
  );

  if (section.type === "hero" || section.type === "video_hero") {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 dark:border-white/20 p-4 space-y-2">
        <TypeBadge />
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white leading-tight">{title || "Título hero"}</h3>
        <p className="text-sm text-slate-500 line-clamp-2">{body || "Subtítulo o descripción principal"}</p>
        {ctaLabel && <span className="inline-block mt-1 px-3 py-1 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-semibold uppercase">{ctaLabel}</span>}
        {section.type === "video_hero" && <p className="text-[9px] text-slate-400 font-bold uppercase">🎬 Video de fondo configurado</p>}
      </div>
    );
  }
  if (section.type === "cards" || section.type === "pricing") {
    const items = Array.isArray(section.props_json?.items)
      ? (section.props_json.items as Array<Record<string,unknown>>).filter((item) => item.status !== "archived")
      : [];
    return (
      <div className="rounded-lg border border-dashed border-slate-300 dark:border-white/20 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-bold text-slate-800 dark:text-slate-200">{title || "Bloque de tarjetas"}</p>
        {items.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {items.slice(0, 3).map((item, idx) => (
              <span key={idx} className="px-2 py-1 bg-slate-100 dark:bg-white/10 rounded-lg text-[9px] font-bold text-slate-600 dark:text-slate-300">
                {safeString(item.title) || `Item ${idx + 1}`}
              </span>
            ))}
            {items.length > 3 && <span className="text-[9px] text-slate-400">+{items.length - 3} más</span>}
          </div>
        )}
      </div>
    );
  }
  if (section.type === "gallery") {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 dark:border-white/20 p-4 space-y-2">
        <TypeBadge />
        {imageUrl
          // eslint-disable-next-line @next/next/no-img-element
          ? <img src={imageUrl} alt="gallery" className="w-full h-24 object-cover rounded-md" />
          : <div className="w-full h-8 rounded-md bg-slate-100 dark:bg-white/5 flex items-center justify-center text-[9px] text-slate-400 font-bold uppercase">Sin imagen configurada</div>
        }
      </div>
    );
  }
  if (section.type === "cta_banner") {
    return (
      <div className="rounded-lg border border-dashed border-emerald-300 dark:border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-900/10 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{title || "Llamado a la Acción"}</p>
        <p className="text-xs text-slate-500 line-clamp-1">{body || "Subtítulo"}</p>
        {ctaLabel && <span className="inline-block px-3 py-1 bg-emerald-600 text-white rounded-lg text-[10px] font-semibold uppercase">{ctaLabel}</span>}
      </div>
    );
  }
  if (section.type === "testimonials") {
    return (
      <div className="rounded-lg border border-dashed border-rose-300 dark:border-rose-500/30 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{title || "Sección de Testimonios"}</p>
        <div className="flex gap-2">
          {[1,2,3].map(i => (
            <div key={i} className="flex-1 h-8 rounded-md bg-slate-100 dark:bg-white/5 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }
  if (section.type === "stats") {
    const stats = Array.isArray(section.props_json?.items) ? section.props_json.items as Array<Record<string,unknown>> : [];
    return (
      <div className="rounded-lg border border-dashed border-teal-300 dark:border-teal-500/30 p-4 space-y-2">
        <TypeBadge />
        <div className="grid grid-cols-3 gap-2">
          {(stats.length > 0 ? stats : [{value: "—", label: "Métrica"}]).slice(0,3).map((s, i) => (
            <div key={i} className="text-center">
              <p className="text-base font-semibold text-teal-600">{safeString(s.value) || "—"}</p>
              <p className="text-[9px] text-slate-400 font-bold uppercase">{safeString(s.label) || "Métrica"}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (section.type === "team") {
    return (
      <div className="rounded-lg border border-dashed border-orange-300 dark:border-orange-500/30 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{title || "Nuestro Equipo"}</p>
        <div className="flex gap-2">
          {[1,2,3,4].map(i => (
            <div key={i} className="size-8 rounded-full bg-orange-100 dark:bg-orange-900/20 border-2 border-white dark:border-slate-800" />
          ))}
        </div>
      </div>
    );
  }
  if (section.type === "countdown") {
    const target = safeString(section.props_json?.target_date);
    return (
      <div className="rounded-lg border border-dashed border-red-300 dark:border-red-500/30 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{title || "Cuenta Regresiva"}</p>
        <div className="flex gap-3">
          {["DD", "HH", "MM", "SS"].map(u => (
            <div key={u} className="text-center">
              <div className="size-10 rounded-md bg-[hsl(var(--destructive))] flex items-center justify-center text-white font-semibold text-sm">00</div>
              <p className="text-[8px] text-slate-400 mt-0.5 font-bold uppercase">{u}</p>
            </div>
          ))}
        </div>
        {target && <p className="text-[9px] text-slate-400">Hasta: {target}</p>}
      </div>
    );
  }
  if (section.type === "faq") {
    const faqs = Array.isArray(section.props_json?.items)
      ? (section.props_json.items as Array<Record<string,unknown>>).filter((item) => item.status !== "archived")
      : [];
    return (
      <div className="rounded-lg border border-dashed border-amber-300 dark:border-amber-500/30 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{title || "Preguntas Frecuentes"}</p>
        {faqs.slice(0,2).map((f, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className="text-amber-500 font-semibold mt-0.5">Q</span>
            <span className="text-slate-600 dark:text-slate-300 line-clamp-1">{safeString(f.q) || "Pregunta"}</span>
          </div>
        ))}
      </div>
    );
  }
  if (section.type === "embed") {
    const embedUrl = safeString(section.props_json?.embed_url);
    return (
      <div className="rounded-lg border border-dashed border-cyan-300 dark:border-cyan-500/30 p-4 space-y-2">
        <TypeBadge />
        {embedUrl
          ? <p className="text-[10px] text-slate-500 font-mono truncate">{embedUrl}</p>
          : <div className="w-full h-8 rounded-md bg-slate-100 dark:bg-white/5 flex items-center justify-center text-[9px] text-slate-400 font-bold uppercase">Sin URL configurada</div>
        }
      </div>
    );
  }
  // rich_text, rich_text_columns, default
  return (
    <div className="rounded-lg border border-dashed border-slate-300 dark:border-white/20 p-4 space-y-2">
      <TypeBadge />
      <h4 className="text-base font-semibold text-slate-800 dark:text-slate-100">{title || "Título"}</h4>
      <p className="text-sm text-slate-500 line-clamp-3">{body || "Contenido de sección"}</p>
      {section.type === "rich_text_columns" && (
        <div className="flex gap-2 mt-1">
          <div className="flex-1 h-2 rounded bg-slate-200 dark:bg-white/10" />
          <div className="flex-1 h-2 rounded bg-slate-200 dark:bg-white/10" />
        </div>
      )}
    </div>
  );
}

function MediaPicker({
  open,
  token,
  selectedUrl,
  onClose,
  onSelect,
}: {
  open: boolean;
  token?: string | null;
  selectedUrl?: string;
  onClose: () => void;
  onSelect: (item: CmsMediaItem) => void;
}) {
  const [items, setItems] = useState<CmsMediaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open || !token) return;
    setLoading(true);
    apiFetch<CmsMediaItem[]>("/cms/media", { token, cache: "no-store" })
      .then((rows) => setItems(Array.isArray(rows) ? rows : []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [open, token]);

  const uploadImage = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !token) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("section", "builder");
      form.append("alt_text", file.name);
      form.append("tags", "builder,imagen");
      const created = await apiFetch<CmsMediaItem>("/cms/media/upload", {
        method: "POST",
        token,
        body: form,
      });
      setItems((prev) => [created, ...prev]);
      onSelect(created);
    } finally {
      setUploading(false);
    }
  };

  const imageItems = items.filter((item) => {
    const mime = item.mime_type || "";
    return mime.startsWith("image/") || /\.(png|jpe?g|webp|gif|svg)$/i.test(item.url);
  });
  const normalizedSearch = search.trim().toLowerCase();
  const filtered = imageItems.filter((item) => {
    if (!normalizedSearch) return true;
    return [item.filename, item.alt_text, item.url, item.section]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(normalizedSearch));
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/50 backdrop-blur-sm p-4 flex items-center justify-center" onClick={onClose}>
      <div className="w-full max-w-5xl max-h-[86vh] overflow-hidden rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-[#111418] border border-slate-200 dark:border-white/10 shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/10 px-3 py-1.5">
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-md bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-blue-300 flex items-center justify-center">
              <ImageIcon size={18} />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Biblioteca CMS</p>
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">Seleccionar imagen</h2>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-md text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10">
            <X size={18} />
          </button>
        </div>

        <div className="flex items-center gap-3 border-b border-slate-200 dark:border-white/10 px-3 py-3">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por archivo, alt text o seccion"
              className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-transparent py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
            />
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-white disabled:opacity-50">
            <Upload size={14} />
            {uploading ? "Subiendo..." : "Subir imagen"}
            <input type="file" accept="image/*" className="hidden" onChange={uploadImage} disabled={uploading} />
          </label>
        </div>

        <div className="max-h-[62vh] overflow-y-auto p-3">
          {loading ? (
            <div className="py-1.5 text-center text-sm font-bold text-slate-400">Cargando biblioteca...</div>
          ) : filtered.length === 0 ? (
            <div className="py-1.5 text-center">
              <FileImage size={34} className="mx-auto text-slate-300" />
              <p className="mt-3 text-sm font-bold text-slate-500">No hay imagenes disponibles.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
              {filtered.map((item) => {
                const isSelected = selectedUrl === item.url;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelect(item)}
                    className={`group text-left rounded-lg border overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-white/[0.03] transition-all ${isSelected ? "border-blue-500 ring-2 ring-blue-500/20" : "border-slate-200 dark:border-white/10 hover:border-blue-300"}`}
                  >
                    <div className="relative aspect-video bg-slate-100 dark:bg-white/5">
                      <img src={item.url} alt={item.alt_text || item.filename || ""} className="h-full w-full object-cover" />
                      {isSelected && (
                        <span className="absolute right-2 top-2 size-7 rounded-full bg-[hsl(var(--primary))] text-white flex items-center justify-center shadow-lg">
                          <Check size={15} />
                        </span>
                      )}
                    </div>
                    <div className="p-3">
                      <p className="truncate text-xs font-semibold text-slate-800 dark:text-slate-100">{item.filename || "Imagen CMS"}</p>
                      <p className="mt-1 truncate text-[10px] text-slate-400">{item.alt_text || item.section || "Sin alt text"}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function CmsBuilderPage() {
  const { token, user } = useAuth();
  const searchParams = useSearchParams();
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<Array<{ site_key: string; name: string; base_path: string }>>([]);
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [activeSlug, setActiveSlug] = useState("");
  const [sections, setSections] = useState<CmsSection[]>([]);
  const [versions, setVersions] = useState<CmsPageVersion[]>([]);
  const [publishLogs, setPublishLogs] = useState<CmsPublishLog[]>([]);
  const [newPageTitle, setNewPageTitle] = useState("");
  const [newSectionType, setNewSectionType] = useState("rich_text");
  const [pageTemplateKey, setPageTemplateKey] = useState("simple");
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [draggedSectionId, setDraggedSectionId] = useState<string | null>(null);
  const [previewDevice, setPreviewDevice] = useState<"desktop" | "mobile">("desktop");
  const [canvasMode, setCanvasMode] = useState<"esquema" | "render">("esquema");
  const [pageTitleDraft, setPageTitleDraft] = useState("");
  const [pageSlugDraft, setPageSlugDraft] = useState("");
  const [seoTitleDraft, setSeoTitleDraft] = useState("");
  const [seoDescriptionDraft, setSeoDescriptionDraft] = useState("");
  const [seoImageDraft, setSeoImageDraft] = useState("");
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const [mediaPickerTarget, setMediaPickerTarget] = useState<"section" | "seo">("section");
  const [activeRightTab, setActiveRightTab] = useState<"config" | "seo" | "ai" | "analytics">("config");
  const [seoKeyword, setSeoKeyword] = useState("");
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiOutput, setAiOutput] = useState("");
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [timeframe, setTimeframe] = useState<"7d" | "30d" | "all">("7d");
  const [heatmapType, setHeatmapType] = useState<"clicks" | "scroll" | "attention">("clicks");
  const [abTestingActive, setAbTestingActive] = useState(false);
  const [abTrafficSplit, setAbTrafficSplit] = useState(50);
  const [serpPreviewDevice, setSerpPreviewDevice] = useState<"desktop" | "mobile">("desktop");
  const [aiTone, setAiTone] = useState("warm");
  const [aiTemplate, setAiTemplate] = useState("aida");
  const [aiImagePrompt, setAiImagePrompt] = useState("");
  const [aiImageResult, setAiImageResult] = useState("");
  const [aiImageGenerating, setAiImageGenerating] = useState(false);

  useEffect(() => {
    const querySite = searchParams?.get("site");
    const queryPage = searchParams?.get("page");
    if (querySite) setSiteKey(querySite);
    if (queryPage) setActiveSlug(queryPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activePage = useMemo(() => pages.find((p) => p.slug === activeSlug) ?? null, [pages, activeSlug]);
  const activeSection = useMemo(() => sections.find((s) => s.id === activeSectionId) ?? null, [sections, activeSectionId]);
  const activeSite = useMemo(() => sites.find((site) => site.site_key === siteKey) ?? null, [sites, siteKey]);
  const canEdit = canEditCms(user?.role);
  const canPublish = canPublishCms(user?.role);

  useEffect(() => {
    setPageTitleDraft(activePage?.title || "");
    setPageSlugDraft(activePage?.slug || "");
    setSeoTitleDraft(safeString(activePage?.seo_json?.meta_title));
    setSeoDescriptionDraft(safeString(activePage?.seo_json?.meta_description));
    setSeoImageDraft(safeString(activePage?.seo_json?.meta_image));
  }, [activePage]);

  const loadPages = async (targetSite: string) => {
    if (!token) return;
    const [nextSites, nextPages] = await Promise.all([listCmsSites(token), listCmsPages(targetSite, token)]);
    setSites((nextSites || []).map((site) => ({ site_key: site.site_key, name: site.name, base_path: site.base_path })));
    setPages(nextPages || []);
    if ((nextPages || []).length > 0 && !activeSlug) {
      setActiveSlug(nextPages[0].slug);
    }
  };

  const loadSectionsAndVersions = async (slug: string) => {
    if (!token || !slug) return;
    const [nextSections, nextVersions, nextPublishLogs] = await Promise.all([
      listCmsSections(siteKey, slug, token),
      listCmsPageVersions(siteKey, slug, token),
      listCmsPagePublishLog(siteKey, slug, token),
    ]);
    const ordered = (nextSections || []).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    setSections(ordered);
    setVersions(nextVersions || []);
    setPublishLogs(nextPublishLogs || []);
    if (ordered.length > 0 && (!activeSectionId || !ordered.some((item) => item.id === activeSectionId))) {
      setActiveSectionId(ordered[0].id);
    }
  };

  useEffect(() => {
    loadPages(siteKey).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteKey, token]);

  useEffect(() => {
    loadSectionsAndVersions(activeSlug).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSlug, token]);

  const seoAnalysis = useMemo(() => {
    const checks: Array<{ id: string; label: string; passed: boolean; tip: string; type: "success" | "warning" | "error" }> = [];
    let score = 0;

    // Check Title
    const titleLen = seoTitleDraft?.length || 0;
    if (titleLen >= 30 && titleLen <= 60) {
      checks.push({ id: "title_len", label: "Longitud del título SEO", passed: true, tip: `Correcto (${titleLen} caracteres).`, type: "success" });
      score += 15;
    } else if (titleLen > 0) {
      checks.push({ id: "title_len", label: "Longitud del título SEO", passed: false, tip: `Tiene ${titleLen} caracteres. Recomendado entre 30 y 60.`, type: "warning" });
      score += 5;
    } else {
      checks.push({ id: "title_len", label: "Título SEO vacío", passed: false, tip: "Por favor define un título SEO para indexación básica.", type: "error" });
    }

    // Check Description
    const descLen = seoDescriptionDraft?.length || 0;
    if (descLen >= 110 && descLen <= 160) {
      checks.push({ id: "desc_len", label: "Longitud de meta descripción", passed: true, tip: `Correcto (${descLen} caracteres).`, type: "success" });
      score += 15;
    } else if (descLen > 0) {
      checks.push({ id: "desc_len", label: "Longitud de meta descripción", passed: false, tip: `Tiene ${descLen} caracteres. Recomendado entre 110 y 160.`, type: "warning" });
      score += 5;
    } else {
      checks.push({ id: "desc_len", label: "Meta descripción vacía", passed: false, tip: "La descripción es clave para convencer en los buscadores.", type: "error" });
    }

    // Check Focus Keyword
    if (seoKeyword.trim()) {
      const kw = seoKeyword.toLowerCase().trim();
      
      // Keyword in Title
      const titleMatch = seoTitleDraft?.toLowerCase().includes(kw) || false;
      if (titleMatch) {
        checks.push({ id: "kw_title", label: "Palabra clave en el título", passed: true, tip: "La palabra clave principal está dentro del título.", type: "success" });
        score += 15;
      } else {
        checks.push({ id: "kw_title", label: "Falta palabra clave en el título", passed: false, tip: `El título SEO no contiene "${seoKeyword}".`, type: "warning" });
      }

      // Keyword in Description
      const descMatch = seoDescriptionDraft?.toLowerCase().includes(kw) || false;
      if (descMatch) {
        checks.push({ id: "kw_desc", label: "Palabra clave en descripción", passed: true, tip: "La palabra clave se encuentra en la meta descripción.", type: "success" });
        score += 15;
      } else {
        checks.push({ id: "kw_desc", label: "Falta palabra clave en descripción", passed: false, tip: `La descripción no contiene "${seoKeyword}".`, type: "warning" });
      }

      // Keyword in Section Contents
      let kwCount = 0;
      sections.forEach(s => {
        const text = (safeString(s.props_json?.title) + " " + safeString(s.props_json?.body)).toLowerCase();
        const occurrences = text.split(kw).length - 1;
        kwCount += occurrences;
      });
      if (kwCount >= 2) {
        checks.push({ id: "kw_content", label: "Densidad de palabra clave", passed: true, tip: `Encontrada ${kwCount} veces en las secciones. Densidad óptima.`, type: "success" });
        score += 15;
      } else if (kwCount === 1) {
        checks.push({ id: "kw_content", label: "Densidad de palabra clave baja", passed: false, tip: `Encontrada solo 1 vez. Añádela en subtítulos o descripciones.`, type: "warning" });
        score += 5;
      } else {
        checks.push({ id: "kw_content", label: "Palabra clave ausente del contenido", passed: false, tip: `No se encuentra "${seoKeyword}" en ninguna sección.`, type: "error" });
      }
    } else {
      checks.push({ id: "kw_none", label: "Sin palabra clave definida", passed: false, tip: "Escribe una palabra clave arriba para analizar el SEO semántico.", type: "warning" });
    }

    // Check Images Alt text
    let totalImages = 0;
    let missingAlt = 0;
    sections.forEach(s => {
      if (s.type === "hero" || s.type === "image_text") {
        const url = safeString(s.props_json?.image_url);
        const alt = safeString(s.props_json?.image_alt);
        if (url) {
          totalImages++;
          if (!alt.trim()) missingAlt++;
        }
      } else if (s.type === "gallery") {
        const items = Array.isArray(s.props_json?.items) ? s.props_json.items : [];
        items.forEach((item: unknown) => {
          const itemObj = asObject(item);
          if (itemObj.url) {
            totalImages++;
            if (!safeString(itemObj.alt).trim()) missingAlt++;
          }
        });
      }
    });

    if (totalImages > 0) {
      if (missingAlt === 0) {
        checks.push({ id: "images_alt", label: "Textos alternativos en imágenes", passed: true, tip: "Todas las imágenes tienen etiqueta alt definida.", type: "success" });
        score += 15;
      } else {
        checks.push({ id: "images_alt", label: "Falta alt text en imágenes", passed: false, tip: `Hay ${missingAlt} de ${totalImages} imágenes sin texto descriptivo alt.`, type: "warning" });
        score += Math.max(0, 15 - missingAlt * 5);
      }
    } else {
      checks.push({ id: "images_alt", label: "Sin imágenes detectadas", passed: true, tip: "No se requiere alt text si no hay imágenes.", type: "success" });
      score += 15;
    }

    // Check headings / hierarchy
    const hasHero = sections.some(s => s.type === "hero" || s.type === "video_hero");
    if (hasHero) {
      checks.push({ id: "hierarchy", label: "Estructura de encabezados", passed: true, tip: "Se detectó sección Hero al inicio (encabezado principal H1).", type: "success" });
      score += 10;
    } else {
      checks.push({ id: "hierarchy", label: "Sin sección Hero principal", passed: false, tip: "Se recomienda un Hero al inicio para jerarquía H1.", type: "warning" });
    }

    return { score: Math.min(100, score), checks };
  }, [seoTitleDraft, seoDescriptionDraft, seoKeyword, sections]);

  const readabilityScore = useMemo(() => {
    let wordCount = 0;
    let sentenceCount = 0;
    sections.forEach(s => {
      const text = safeString(s.props_json?.title) + " " + safeString(s.props_json?.body);
      wordCount += text.split(/\s+/).filter(Boolean).length;
      sentenceCount += text.split(/[.!?]+/).filter(Boolean).length;
    });
    if (wordCount === 0) return { score: 100, label: "Sin contenido" };
    const avgSentenceLength = wordCount / Math.max(1, sentenceCount);
    const score = Math.max(0, Math.min(100, Math.round(206.835 - 1.015 * avgSentenceLength - 84.6)));
    let label = "Fácil de leer";
    if (score < 50) label = "Complejo / Académico";
    else if (score < 75) label = "Estándar";
    else label = "Muy fácil de leer";
    return { score, label };
  }, [sections]);

  const handleAiGenerate = async () => {
    if (!aiPrompt.trim()) return;
    setAiGenerating(true);
    setAiOutput("");

    try {
      const toneLabels: Record<string, string> = {
        inspiration: "Inspiracional & Espiritual",
        formal: "Institucional & Respetuoso",
        warm: "Cercano & Familiar",
        dynamic: "Joven & Moderno"
      };

      const toneText = toneLabels[aiTone] || "Cercano & Familiar";
      const pageTitle = pageTitleDraft || activePage?.title || "Nuestra Iglesia";
      const kw = aiPrompt.trim();

      let fullPrompt = "";
      if (aiTemplate === "aida") {
        fullPrompt = `Genera contenido editorial usando el modelo AIDA (Atención-Interés-Deseo-Acción) con tono ${toneText} para la página "${pageTitle}" sobre: ${kw}. Incluye un título sugerido y un texto para botón CTA al final.`;
      } else if (aiTemplate === "pas") {
        fullPrompt = `Genera contenido editorial usando el modelo PAS (Problema-Agitación-Solución) con tono ${toneText} para la página "${pageTitle}" sobre: ${kw}. Incluye un título sugerido y un texto para botón CTA al final.`;
      } else if (aiTemplate === "headlines") {
        fullPrompt = `Genera 5 titulares impactantes en tono ${toneText} para una sección Hero de la página "${pageTitle}" relacionada con: ${kw}. Numera cada propuesta.`;
      } else if (aiTemplate === "improve") {
        fullPrompt = `Mejora el siguiente texto con un tono más profesional, persuasivo y en tono ${toneText}: "${kw}". Devuelve el texto mejorado directamente.`;
      }

      const result = await apiFetch<{ response: string }>("/system/ai/generate", {
        method: "POST",
        token,
        body: { prompt: fullPrompt, context: `Página: ${pageTitle}, Plantilla: ${aiTemplate}, Tono: ${toneText}` },
      });

      if (result?.response) {
        setAiOutput(result.response);
      } else {
        throw new Error("Respuesta vacía de la IA");
      }
    } catch (err) {
      // Fallback: usar contenido mock si el endpoint no está disponible
      console.warn("FaroGPT endpoint failed, using fallback:", err);
      const toneLabels: Record<string, string> = {
        inspiration: "Inspiracional & Espiritual",
        formal: "Institucional & Respetuoso",
        warm: "Cercano & Familiar",
        dynamic: "Joven & Moderno"
      };
      const toneText = toneLabels[aiTone] || "Cercano & Familiar";
      const pageTitle = pageTitleDraft || activePage?.title || "Nuestra Iglesia";
      const kw = aiPrompt.trim();
      let fallbackText = "";

      if (aiTemplate === "aida") {
        fallbackText = `### 🌟 MODELO AIDA (Tono: ${toneText}) 🌟\n\n` +
                 `**[ATENCIÓN]**\n` +
                 `¿Buscas un lugar donde pertenecer y crecer de verdad? Descubre una comunidad apasionada en ${pageTitle} que te recibe con los brazos abiertos.\n\n` +
                 `**[INTERÉS]**\n` +
                 `Aquí no solo vienes a escuchar; vienes a conectar. Con grupos de crecimiento adaptados a tu etapa de vida, enseñanzas relevantes basadas en la Palabra de Dios y proyectos sociales en los que puedes activar tus dones, encontrarás un espacio para vivir tu fe de manera activa y real: "${kw}".\n\n` +
                 `**[DESEO]**\n` +
                 `Imagina caminar al lado de personas que comparten tus valores, te apoyan en tus dificultades y celebran tus victorias. Un lugar donde tu familia puede florecer y donde tu propósito de vida se alinea con el plan de Dios.\n\n` +
                 `**[ACCIÓN]**\n` +
                 `¡Haz clic en el botón de abajo y acompáñanos en nuestra próxima reunión! Te estamos esperando.\n\n` +
                 `**Título:** ¡Te damos la Bienvenida a Casa!\n` +
                 `**Botón:** Planificar Visita`;
      } else if (aiTemplate === "pas") {
        fallbackText = `### 🎯 MODELO PAS: Problema-Agitación-Solución (Tono: ${toneText}) 🎯\n\n` +
                 `**[PROBLEMA]**\n` +
                 `En un mundo hiperconectado pero cada vez más aislado, es fácil sentirse solo, abrumado o sin un rumbo espiritual claro.\n\n` +
                 `**[AGITACIÓN]**\n` +
                 `El ritmo acelerado del día a día nos aleja de lo que realmente importa. La falta de propósito y la ausencia de una comunidad de apoyo real terminan desgastando nuestra fe y nuestras relaciones familiares.\n\n` +
                 `**[SOLUCIÓN]**\n` +
                 `En ${pageTitle}, creemos que fuimos creados para la comunión. A través de nuestra iniciativa de "${kw}", te ofrecemos una ruta clara de integración, apoyo pastoral y grupos pequeños donde sanar, crecer y servir con gozo.\n\n` +
                 `**Título:** Encuentra Conexión y Propósito Real\n` +
                 `**Mensaje Principal:** Una comunidad viva y comprometida para apoyarte en cada paso de tu vida espiritual.\n` +
                 `**Botón:** Conectar Ahora`;
      } else if (aiTemplate === "headlines") {
        fallbackText = `### ✍️ TITULARES OPTIMIZADOS PARA HERO (Tono: ${toneText}) ✍️\n\n` +
                 `Propuestas premium basadas en tu búsqueda "${kw}":\n\n` +
                 `1. **Propuesta de Impacto:** "Una casa de esperanza, una familia para crecer."\n` +
                 `2. **Propuesta Espiritual:** "Conectando corazones con el propósito eterno de Dios."\n` +
                 `3. **Propuesta Comunitaria:** "Tu lugar de encuentro en ${pageTitle}. ¡Bienvenidos a casa!"\n` +
                 `4. **Propuesta Dinámica:** "Fe activa, relaciones reales, impacto real."\n` +
                 `5. **Propuesta Corta & Fuerte:** "Crecer en fe, servir con amor."\n\n` +
                 `*Selecciona cualquiera de estos titulares para copiarlo directamente en tu sección Hero.*`;
      } else if (aiTemplate === "improve") {
        fallbackText = `### ✨ TEXTO MEJORADO POR FAROGPT (Tono: ${toneText}) ✨\n\n` +
                 `**Texto Original Analizado:**\n` +
                 `"${kw}"\n\n` +
                 `**Versión Optimizada y Pulida:**\n` +
                 `Queremos invitarte a ser parte activa de lo que Dios está haciendo en nuestra casa. A través de esta iniciativa en ${pageTitle}, no solo encontrarás un canal para canalizar tu vocación de servicio, sino también una comunidad dispuesta a caminar contigo. Creemos firmemente que cada pequeño esfuerzo sumado produce una gran transformación.\n\n` +
                 `*Este texto ha sido enriquecido para mejorar la retención de usuarios y el impacto emocional.*`;
      }
      setAiOutput(fallbackText);
    } finally {
      setAiGenerating(false);
    }
  };

  const handleAiImageGenerate = () => {
    if (!aiImagePrompt.trim()) return;
    setAiImageGenerating(true);
    setAiImageResult("");

    const term = aiImagePrompt.toLowerCase().trim();

    // Unsplash image categories for church/CMS content
    const imageMap: Record<string, string[]> = {
      default: ["https://images.unsplash.com/photo-1438232992991-995b7058bbb3?auto=format&fit=crop&w=1200&q=80"],
      children: [
        "https://images.unsplash.com/photo-1472241139007-df4e38e764f2?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=1200&q=80",
      ],
      music: [
        "https://images.unsplash.com/photo-1465847899084-d164df4dedc6?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?auto=format&fit=crop&w=1200&q=80",
      ],
      community: [
        "https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1540575467063-178a50c2df87?auto=format&fit=crop&w=1200&q=80",
      ],
      bible: [
        "https://images.unsplash.com/photo-1504052434569-70ad58c63172?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1532619675605-1ede6c2ed2b0?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1469583985357-2db70eafa4b0?auto=format&fit=crop&w=1200&q=80",
      ],
      youth: [
        "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1560523159-4a9692d222f9?auto=format&fit=crop&w=1200&q=80",
      ],
      nature: [
        "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1200&q=80",
      ],
      prayer: [
        "https://images.unsplash.com/photo-1478040049072-2c2cf0a143db?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1499728603263-13726abce5fd?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1504052434569-70ad58c63172?auto=format&fit=crop&w=1200&q=80",
      ],
      church: [
        "https://images.unsplash.com/photo-1438232992991-995b7058bbb3?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1507537362848-9c7e70b7b5c1?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1548624313-edb1d0e9e3b9?auto=format&fit=crop&w=1200&q=80",
      ],
      hands: [
        "https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1559027615-cd4628902d4a?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?auto=format&fit=crop&w=1200&q=80",
      ],
      family: [
        "https://images.unsplash.com/photo-1511895426328-dc8714191300?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1476703993599-0035a21b17a9?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1529636798458-92182e662485?auto=format&fit=crop&w=1200&q=80",
      ],
      hero: [
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1200&q=80",
      ],
    };

    const categories: Array<{ keys: string[]; name: string }> = [
      { keys: ["niño", "kids", "children", "infant", "niños", "infantes"], name: "children" },
      { keys: ["musica", "worship", "adoracion", "cantar", "music", "alabanza"], name: "music" },
      { keys: ["comunidad", "community", "grupo", "reunion", "people", "personas"], name: "community" },
      { keys: ["biblia", "bible", "estudio", "study", "lectura", "reading"], name: "bible" },
      { keys: ["jovenes", "youth", "jóvenes", "chicos", "adolescent"], name: "youth" },
      { keys: ["naturaleza", "nature", "creacion", "creation", "paisaje", "landscape"], name: "nature" },
      { keys: ["oracion", "prayer", "oración", "rezar", "pray"], name: "prayer" },
      { keys: ["iglesia", "church", "templo", "temple"], name: "church" },
      { keys: ["manos", "hands", "ayuda", "help", "voluntario", "volunteer", "servicio"], name: "hands" },
      { keys: ["familia", "family", "hogar", "home"], name: "family" },
      { keys: ["hero", "heroe", "héroe", "banner", "portada", "cover"], name: "hero" },
    ];

    const matched = categories.find(c => c.keys.some(k => term.includes(k)));
    const pool = matched ? imageMap[matched.name] : imageMap.default;
    const url = pool[Math.floor(Math.random() * pool.length)];

    setAiImageResult(url);
    setAiImageGenerating(false);
  };

  const handleInsertAiAsSection = async () => {
    if (!aiOutput || !token || !activeSlug || !canEdit) return;
    setSaving(true);
    try {
      const lines = aiOutput.split("\n");
      const titleLine = lines.find(l => l.startsWith("**Título:**") || l.startsWith("###")) || "";
      const cleanTitle = titleLine.replace(/\*\*Título:\*\*|###|✨|📋|❤️|🤝/g, "").trim() || "Sección Generada con IA";
      
      const bodyLines = lines.filter(l => !l.startsWith("###") && !l.startsWith("**Título:**") && !l.startsWith("✨") && !l.startsWith("📋") && !l.startsWith("❤️") && !l.startsWith("🤝"));
      const cleanBody = bodyLines.join("\n").replace(/\*\*Mensaje:\*\*|\*\*Mensaje Principal:\*\*/g, "").trim();

      await createCmsSection(
        siteKey,
        activeSlug,
        {
          type: "rich_text",
          sort_order: sections.length,
          props_json: { title: cleanTitle, body: cleanBody, cta_label: "Saber más", cta_href: "/" },
        },
        token,
      );
      await loadSectionsAndVersions(activeSlug);
      setActiveRightTab("config");
    } finally {
      setSaving(false);
    }
  };

  const handleReplaceActiveSectionWithAi = async () => {
    if (!aiOutput || !activeSection || !token || !activeSlug || !canEdit) return;
    setSaving(true);
    try {
      const lines = aiOutput.split("\n");
      const titleLine = lines.find(l => l.startsWith("**Título:**") || l.startsWith("###")) || "";
      const cleanTitle = titleLine.replace(/\*\*Título:\*\*|###|✨|📋|❤️|🤝/g, "").trim() || (activeSection.props_json?.title as string) || "Sección Actualizada";
      
      const bodyLines = lines.filter(l => !l.startsWith("###") && !l.startsWith("**Título:**") && !l.startsWith("✨") && !l.startsWith("📋") && !l.startsWith("❤️") && !l.startsWith("🤝"));
      const cleanBody = bodyLines.join("\n").replace(/\*\*Mensaje:\*\*|\*\*Mensaje Principal:\*\*/g, "").trim();

      const nextProps = {
        ...(activeSection.props_json || {}),
        title: cleanTitle,
        body: cleanBody,
      };
      await patchCmsSection(siteKey, activeSlug, activeSection.id, { props_json: nextProps }, token);
      await loadSectionsAndVersions(activeSlug);
    } finally {
      setSaving(false);
    }
  };

  const createPage = async () => {
    if (!token || !newPageTitle.trim() || !canEdit) return;
    const slug = newPageTitle.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    if (!slug) return;
    const row = await createCmsPage(siteKey, { slug, title: newPageTitle }, token);
    setNewPageTitle("");
    await loadPages(siteKey);
    setActiveSlug(row.slug);
  };

  const createPageFromTemplate = async () => {
    if (!token || !newPageTitle.trim() || !canEdit) return;
    const slug = newPageTitle.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    if (!slug) return;
    const page = await createCmsPage(siteKey, { slug, title: newPageTitle }, token);
    const template = PAGE_TEMPLATES.find((item) => item.key === pageTemplateKey);
    if (template) {
      for (let i = 0; i < template.sections.length; i += 1) {
        const section = template.sections[i];
        await createCmsSection(
          siteKey,
          page.slug,
          {
            type: section.type,
            sort_order: i,
            props_json: section.props_json,
          },
          token,
        );
      }
    }
    setNewPageTitle("");
    await loadPages(siteKey);
    setActiveSlug(page.slug);
    await loadSectionsAndVersions(page.slug);
  };

  const addSection = async () => {
    if (!token || !activeSlug || !canEdit) return;
    await createCmsSection(
      siteKey,
      activeSlug,
      {
        type: newSectionType,
        sort_order: sections.length,
        props_json: { title: "Nueva sección", body: "Edita este contenido", cta_label: "Ver más", cta_href: "/" },
      },
      token,
    );
    await loadSectionsAndVersions(activeSlug);
  };

  const addTemplateSection = async (template: { type: string; props_json: Record<string, unknown> }) => {
    if (!token || !activeSlug || !canEdit) return;
    await createCmsSection(
      siteKey,
      activeSlug,
      {
        type: template.type,
        sort_order: sections.length,
        props_json: template.props_json,
      },
      token,
    );
    await loadSectionsAndVersions(activeSlug);
  };

  const saveSectionField = async (field: string, value: string) => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    setSaving(true);
    const nextProps = { ...(activeSection.props_json || {}), [field]: value };
    try {
      await patchCmsSection(siteKey, activeSlug, activeSection.id, { props_json: nextProps }, token);
      await loadSectionsAndVersions(activeSlug);
    } finally {
      setSaving(false);
    }
  };

  const saveSectionProps = async (nextProps: Record<string, unknown>) => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    setSaving(true);
    try {
      await patchCmsSection(siteKey, activeSlug, activeSection.id, { props_json: nextProps }, token);
      await loadSectionsAndVersions(activeSlug);
    } finally {
      setSaving(false);
    }
  };

  const updateSectionPropsLocal = (nextProps: Record<string, unknown>) => {
    if (!activeSection) return;
    setSections((prev) => prev.map((section) => section.id === activeSection.id ? { ...section, props_json: nextProps } : section));
  };

  const upsertArrayItem = (
    key: "items",
    index: number,
    patch: Record<string, unknown>,
  ) => {
    if (!activeSection) return;
    const currentProps = asObject(activeSection.props_json);
    const currentItems = Array.isArray(currentProps[key]) ? [...(currentProps[key] as Array<Record<string, unknown>>)] : [];
    const currentItem = asObject(currentItems[index]);
    currentItems[index] = { ...currentItem, ...patch };
    const nextProps = { ...currentProps, [key]: currentItems };
    updateSectionPropsLocal(nextProps);
    return nextProps;
  };

  const addArrayItem = (key: "items", template: Record<string, unknown>) => {
    if (!activeSection) return;
    const currentProps = asObject(activeSection.props_json);
    const currentItems = Array.isArray(currentProps[key]) ? [...(currentProps[key] as Array<Record<string, unknown>>)] : [];
    const nextItems = [...currentItems, template];
    const nextProps = { ...currentProps, [key]: nextItems };
    updateSectionPropsLocal(nextProps);
    return nextProps;
  };

  const setSectionVisibility = async (visible: boolean) => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    await patchCmsSection(siteKey, activeSlug, activeSection.id, { is_visible: visible }, token);
    await loadSectionsAndVersions(activeSlug);
  };

  const toggleSectionArchive = async () => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    const nextStatus = activeSection.status === "archived" ? "active" : "archived";
    await patchCmsSection(siteKey, activeSlug, activeSection.id, { status: nextStatus }, token);
    await loadSectionsAndVersions(activeSlug);
  };

  const duplicateSection = async () => {
    if (!token || !activeSlug || !activeSection || !canEdit) return;
    await createCmsSection(
      siteKey,
      activeSlug,
      {
        type: activeSection.type,
        sort_order: sections.length,
        props_json: { ...(activeSection.props_json || {}) },
      },
      token,
    );
    await loadSectionsAndVersions(activeSlug);
  };

  const moveSection = async (sectionId: string, direction: "up" | "down") => {
    if (!canEdit) return;
    const idx = sections.findIndex((s) => s.id === sectionId);
    if (idx < 0) return;
    const targetIdx = direction === "up" ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= sections.length) return;
    const next = [...sections];
    const current = next[idx];
    next[idx] = next[targetIdx];
    next[targetIdx] = current;
    const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
    setSections(next.map((item, index) => ({ ...item, sort_order: index })));
    if (!token || !activeSlug) return;
    await reorderCmsSections(siteKey, activeSlug, payload, token);
    await loadSectionsAndVersions(activeSlug);
  };

  const moveSectionToIndex = async (sourceId: string, targetId: string) => {
    if (!canEdit) return;
    const sourceIndex = sections.findIndex((s) => s.id === sourceId);
    const targetIndex = sections.findIndex((s) => s.id === targetId);
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;
    const next = [...sections];
    const [moved] = next.splice(sourceIndex, 1);
    next.splice(targetIndex, 0, moved);
    const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
    setSections(next.map((item, index) => ({ ...item, sort_order: index })));
    if (!token || !activeSlug) return;
    await reorderCmsSections(siteKey, activeSlug, payload, token);
    await loadSectionsAndVersions(activeSlug);
  };

  const runWorkflow = async (action: "submit_review" | "approve" | "publish" | "archive" | "revert_draft") => {
    if (!token || !activeSlug) return;
    if (["approve", "publish", "archive"].includes(action) && !canPublish) return;
    if (!["approve", "publish", "archive"].includes(action) && !canEdit) return;
    await workflowCmsPage(siteKey, activeSlug, action, note || undefined, token);
    await loadPages(siteKey);
    await loadSectionsAndVersions(activeSlug);
    setNote("");
  };

  const rollback = async (versionId: string) => {
    if (!token || !activeSlug || !canPublish) return;
    await rollbackCmsPageVersion(siteKey, activeSlug, versionId, token);
    await loadPages(siteKey);
    await loadSectionsAndVersions(activeSlug);
  };

  const savePageMetadata = async () => {
    if (!token || !activePage || !canEdit) return;
    const slug = pageSlugDraft.toLowerCase().trim().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    if (!slug) return;
    const seo_json = {
      ...asObject(activePage.seo_json),
      meta_title: seoTitleDraft.trim(),
      meta_description: seoDescriptionDraft.trim(),
      meta_image: seoImageDraft.trim(),
    };
    const updated = await patchCmsPage(
      siteKey,
      activePage.slug,
      { title: pageTitleDraft || activePage.title, slug, seo_json },
      token,
    );
    await loadPages(siteKey);
    setActiveSlug(updated.slug);
  };

  const togglePageArchive = async () => {
    if (!token || !activePage || !canEdit) return;
    const action = activePage.status === "archived" ? "revert_draft" : "archive";
    const notes = activePage.status === "archived" ? "Restaurada desde builder" : "Archivada desde builder";
    await workflowCmsPage(siteKey, activePage.slug, action, notes, token);
    await loadPages(siteKey);
    setActiveSlug(activePage.slug);
  };

  return (
    <div className="space-y-3 p-3">
      <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418] p-3 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">CMS V2 Builder</p>
          <h1 className="mt-2 text-lg font-semibold">Constructor visual multisitio</h1>
        </div>
        <div className="rounded-md bg-primary/10 px-3 py-2 text-primary text-xs font-semibold uppercase tracking-wide inline-flex items-center gap-2">
          <LayoutPanelTop size={14} /> Beta
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        <aside className="lg:col-span-3 rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418] p-4 space-y-3">
          <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Sitio</label>
          <select value={siteKey} onChange={(e) => setSiteKey(e.target.value)} className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm">
            {sites.length === 0 && <option value={SITE_KEY}>{SITE_KEY}</option>}
            {sites.map((site) => (
              <option key={site.site_key} value={site.site_key}>{site.name} ({site.site_key})</option>
            ))}
          </select>

          <div className="rounded-md border border-slate-200 dark:border-white/10 p-3 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Nueva página</p>
            <input value={newPageTitle} onChange={(e) => setNewPageTitle(e.target.value)} placeholder="Ej: Página de bienvenida" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm" disabled={!canEdit} />
            <button onClick={createPage} disabled={!canEdit} className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white disabled:opacity-50"><Plus size={12} /> Crear vacía</button>
            <select value={pageTemplateKey} onChange={(e) => setPageTemplateKey(e.target.value)} className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs">
              {PAGE_TEMPLATES.map((template) => (
                <option key={template.key} value={template.key}>{template.label}</option>
              ))}
            </select>
            <button onClick={createPageFromTemplate} disabled={!canEdit} className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50">
              <Plus size={12} /> Crear con plantilla
            </button>
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Páginas</p>
            {pages.map((page) => (
              <button key={page.id} onClick={() => setActiveSlug(page.slug)} className={`w-full text-left rounded-lg border px-3 py-2 text-sm ${activeSlug === page.slug ? "border-primary/40 bg-primary/5" : "border-slate-200 dark:border-white/10"}`}>
                <p className="font-bold">{page.title}</p>
                <p className="text-[10px] uppercase tracking-wide text-slate-400">/{page.slug} · {page.status}</p>
              </button>
            ))}
          </div>

          <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-white/10">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Plantillas rápidas</p>
            {SECTION_TEMPLATES.map((template) => (
              <button
                key={template.label}
                onClick={() => addTemplateSection(template)}
                disabled={!activeSlug || !canEdit}
                className="w-full text-left rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-xs font-bold hover:border-primary/40 transition-all disabled:opacity-50"
              >
                {template.label}
              </button>
            ))}
          </div>
        </aside>

        <section className="lg:col-span-6 rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418] p-4 space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Canvas · {activeSlug ? `/${activeSlug}` : "Selecciona página"}</h2>
            <div className="flex items-center gap-2">
              {/* Canvas mode toggle */}
              <div className="inline-flex rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden">
                <button
                  onClick={() => setCanvasMode("esquema")}
                  className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${canvasMode === "esquema" ? "bg-primary text-white" : "bg-transparent"}`}
                  title="Vista esquemática"
                >
                  <LayoutPanelTop size={11} /> Esquema
                </button>
                <button
                  onClick={() => setCanvasMode("render")}
                  className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${canvasMode === "render" ? "bg-primary text-white" : "bg-transparent"}`}
                  title="Vista render real"
                >
                  <Eye size={11} /> Render
                </button>
              </div>
              {/* Device toggle */}
              <div className="inline-flex rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden">
                <button
                  onClick={() => setPreviewDevice("desktop")}
                  className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${previewDevice === "desktop" ? "bg-primary text-white" : "bg-transparent"}`}
                >
                  <Monitor size={11} /> Desktop
                </button>
                <button
                  onClick={() => setPreviewDevice("mobile")}
                  className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${previewDevice === "mobile" ? "bg-primary text-white" : "bg-transparent"}`}
                >
                  <Smartphone size={11} /> Mobile
                </button>
              </div>
              <select value={newSectionType} onChange={(e) => setNewSectionType(e.target.value)} className="rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm">
                {SECTION_TYPES.map((type) => <option key={type} value={type}>{SECTION_TYPE_LABEL[type] ?? type}</option>)}
              </select>
              <button onClick={addSection} disabled={!activeSlug || !canEdit} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50">
                <Plus size={12} /> Añadir
              </button>
            </div>
          </div>

          <div className={`space-y-3 ${previewDevice === "mobile" ? "max-w-[420px] mx-auto" : ""}`}>
            {sections.map((section) => (
              <div
                key={section.id}
                draggable={canEdit}
                onDragStart={() => setDraggedSectionId(section.id)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={async () => {
                  if (draggedSectionId && draggedSectionId !== section.id) {
                    await moveSectionToIndex(draggedSectionId, section.id);
                  }
                  setDraggedSectionId(null);
                }}
                onDragEnd={() => setDraggedSectionId(null)}
                className={`rounded-md border p-3 cursor-grab active:cursor-grabbing ${section.status === "archived" ? "opacity-70 border-amber-200 bg-amber-50/40 dark:bg-amber-500/5" : section.id === activeSectionId ? "border-primary/40 bg-primary/5" : "border-slate-200 dark:border-white/10"}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <button onClick={() => setActiveSectionId(section.id)} className="text-left">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                      {section.type} {section.status === "archived" ? "· archivada" : ""}
                    </p>
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{safeString(section.props_json?.title) || "Sección"}</p>
                  </button>
                  <div className="flex items-center gap-1">
                    <button onClick={() => moveSection(section.id, "up")} disabled={!canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 p-1.5 disabled:opacity-50"><ArrowUp size={12} /></button>
                    <button onClick={() => moveSection(section.id, "down")} disabled={!canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 p-1.5 disabled:opacity-50"><ArrowDown size={12} /></button>
                  </div>
                </div>
                <div className="relative mt-3">
                  {canvasMode === "render" ? (
                    <SectionRenderPreview section={section} mobile={previewDevice === "mobile"} />
                  ) : (
                    <SectionPreview section={section} />
                  )}
                  {showHeatmap && (
                    <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden rounded-lg">
                      {heatmapType === "clicks" && (
                        <div className="absolute inset-0 bg-red-500/[0.02] backdrop-blur-[0.2px]">
                          <div className="absolute top-1/4 left-1/4 w-12 h-12 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.75)_0%,rgba(245,158,11,0.4)_50%,rgba(0,0,0,0)_100%)] animate-pulse inline-flex items-center justify-center"><span className="text-[7px] text-white font-bold opacity-60">72%</span></div>
                          <div className="absolute top-2/3 left-1/2 w-18 h-18 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.65)_0%,rgba(16,185,129,0.3)_60%,rgba(0,0,0,0)_100%)]" style={{ animationDelay: "300ms" }} />
                          <div className="absolute top-1/3 left-2/3 w-14 h-14 rounded-full bg-[radial-gradient(circle,rgba(59,130,246,0.65)_0%,rgba(0,0,0,0)_80%)]" style={{ animationDelay: "600ms" }} />
                          <div className="absolute top-1/2 left-[80%] w-10 h-10 rounded-full bg-[radial-gradient(circle,rgba(245,158,11,0.75)_0%,rgba(0,0,0,0)_90%)]" />
                        </div>
                      )}
                      {heatmapType === "scroll" && (
                        <div className="absolute inset-0 flex flex-col justify-between text-[8px] font-bold text-white/90">
                          <div className="w-full h-[25%] bg-gradient-to-b from-emerald-500/20 to-transparent border-t border-emerald-500/40 p-1">100% de usuarios visualizan esta zona (Above the fold)</div>
                          <div className="w-full h-[25%] bg-gradient-to-b from-yellow-500/20 to-transparent border-t border-yellow-500/40 p-1">78% de usuarios se desplazan hasta aquí</div>
                          <div className="w-full h-[25%] bg-gradient-to-b from-orange-500/20 to-transparent border-t border-orange-500/40 p-1">45% de usuarios continúan leyendo</div>
                          <div className="w-full h-[25%] bg-gradient-to-b from-red-500/20 to-red-500/5 border-t border-red-500/40 p-1">22% de usuarios llegan al final</div>
                        </div>
                      )}
                      {heatmapType === "attention" && (
                        <div className="absolute inset-0 bg-blue-500/[0.02]">
                          <div className="absolute top-[30%] left-[20%] w-32 h-32 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.45)_0%,rgba(245,158,11,0.25)_40%,rgba(59,130,246,0.1)_70%,transparent_100%)] blur-[4px]" />
                          <div className="absolute top-[60%] left-[60%] w-44 h-44 rounded-full bg-[radial-gradient(circle,rgba(245,158,11,0.4)_0%,rgba(16,185,129,0.2)_50%,transparent_100%)] blur-[6px]" />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {sections.length === 0 && <p className="text-sm text-slate-500">No hay secciones en esta página.</p>}
            {sections.length > 0 && (
              <div
                onDragOver={(event) => event.preventDefault()}
                onDrop={async () => {
                  if (!canEdit || !token || !activeSlug || !draggedSectionId) return;
                  const moved = sections.find((item) => item.id === draggedSectionId);
                  if (!moved) return;
                  const next = [...sections.filter((item) => item.id !== draggedSectionId), moved];
                  const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
                  await reorderCmsSections(siteKey, activeSlug, payload, token);
                  setDraggedSectionId(null);
                  await loadSectionsAndVersions(activeSlug);
                }}
                className="rounded-md border border-dashed border-slate-300 dark:border-white/20 p-3 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400"
              >
                Soltar aquí para mover al final
              </div>
            )}
          </div>
        </section>

        <aside className="lg:col-span-3 rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418] p-4 space-y-4 max-h-[90vh] overflow-y-auto">
          {/* Tab Selection Header */}
          <div className="flex border-b border-slate-200 dark:border-white/10 pb-2 gap-1 overflow-x-auto">
            <button
              onClick={() => setActiveRightTab("config")}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all ${activeRightTab === "config" ? "bg-[hsl(var(--primary))] text-white" : "text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5"}`}
            >
              <Settings size={12} /> Config
            </button>
            <button
              onClick={() => setActiveRightTab("seo")}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all ${activeRightTab === "seo" ? "bg-[hsl(var(--primary))] text-white" : "text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5"}`}
            >
              <Sparkles size={12} /> SEO
            </button>
            <button
              onClick={() => setActiveRightTab("ai")}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all ${activeRightTab === "ai" ? "bg-[hsl(var(--primary))] text-white" : "text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5"}`}
            >
              <Wand2 size={12} /> FaroGPT
            </button>
            <button
              onClick={() => setActiveRightTab("analytics")}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all ${activeRightTab === "analytics" ? "bg-[hsl(var(--primary))] text-white" : "text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5"}`}
            >
              <BarChart3 size={12} /> Métricas
            </button>
          </div>

          {/* TAB 1: CONFIG */}
          {activeRightTab === "config" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Estado página</p>
                <p className="text-sm font-bold">{activePage?.title || "Sin página"}</p>
                <p className="text-[10px] uppercase tracking-wide text-slate-400">{activePage?.status || "-"}</p>
                <input
                  value={pageTitleDraft}
                  onChange={(e) => setPageTitleDraft(e.target.value)}
                  placeholder="Título de página"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />
                <input
                  value={pageSlugDraft}
                  onChange={(e) => setPageSlugDraft(e.target.value)}
                  placeholder="slug-de-pagina"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />
                <div className="rounded-md border border-slate-200 dark:border-white/10 p-3 space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">SEO Básico</p>
                  <input
                    value={seoTitleDraft}
                    onChange={(e) => setSeoTitleDraft(e.target.value)}
                    placeholder="Titulo SEO"
                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                  />
                  <textarea
                    value={seoDescriptionDraft}
                    onChange={(e) => setSeoDescriptionDraft(e.target.value)}
                    placeholder="Descripcion para buscadores y redes"
                    className="w-full min-h-[72px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                  />
                  {seoImageDraft ? (
                    <div className="overflow-hidden rounded-md border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5">
                      <img src={seoImageDraft} alt="Imagen SEO" className="h-24 w-full object-cover" />
                    </div>
                  ) : (
                    <div className="rounded-md border border-dashed border-slate-300 dark:border-white/20 bg-slate-50 dark:bg-white/5 p-3 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">
                      Sin imagen social
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setMediaPickerTarget("seo");
                      setMediaPickerOpen(true);
                    }}
                    disabled={!canEdit}
                    className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <ImageIcon size={13} /> Elegir imagen SEO
                  </button>
                  <input
                    value={seoImageDraft}
                    onChange={(e) => setSeoImageDraft(e.target.value)}
                    placeholder="URL de imagen social"
                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                  />
                </div>
                <button
                  onClick={savePageMetadata}
                  disabled={!activePage || !canEdit}
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50"
                >
                  Guardar pagina/SEO
                </button>
                <textarea value={note} onChange={(e) => setNote(e.target.value)} disabled={!canEdit && !canPublish} placeholder="Nota para workflow..." className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs disabled:opacity-60" />
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => runWorkflow("submit_review")} disabled={!activeSlug || !canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"><Send size={11} /> Review</button>
                  <button onClick={() => runWorkflow("approve")} disabled={!activeSlug || !canPublish} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"><Save size={11} /> Aprobar</button>
                  <button onClick={() => runWorkflow("publish")} disabled={!activeSlug || !canPublish} className="rounded-lg bg-primary text-white px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"><Upload size={11} /> Publicar</button>
                  <button onClick={() => runWorkflow("revert_draft")} disabled={!activeSlug || !canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"><Undo2 size={11} /> Draft</button>
                  <button onClick={() => runWorkflow("archive")} disabled={!activeSlug || !canPublish} className="col-span-2 rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50">Archivar</button>
                </div>
                <button
                  onClick={() => {
                    if (!activeSlug) return;
                    window.open(`/plataforma/cms/preview?site=${encodeURIComponent(siteKey)}&page=${encodeURIComponent(activeSlug)}`, "_blank");
                  }}
                  disabled={!activeSlug}
                  className="w-full rounded-lg border border-blue-200 text-[hsl(var(--primary))] px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <Eye size={11} /> Vista previa borrador
                </button>
                <button
                  onClick={() => {
                    if (!activeSlug) return;
                    const base = activeSite?.base_path || `/${siteKey}`;
                    const normalized = base.endsWith("/") ? base.slice(0, -1) : base;
                    window.open(`${normalized}/${activeSlug}`, "_blank");
                  }}
                  disabled={!activeSlug}
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <ExternalLink size={11} /> Ver página pública
                </button>
                <button
                  onClick={togglePageArchive}
                  disabled={!activePage || !canEdit}
                  className={`w-full rounded-lg border px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50 ${activePage?.status === "archived" ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}
                >
                  {activePage?.status === "archived" ? "Restaurar pagina" : "Archivar pagina"}
                </button>
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-white/10">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Versiones</p>
                <div className="max-h-40 overflow-auto space-y-2 pr-1">
                  {versions.map((version) => (
                    <button key={version.id} onClick={() => rollback(version.id)} disabled={!canPublish} className="w-full rounded-lg border border-slate-200 dark:border-white/10 p-2 text-left text-xs hover:border-primary/40 transition-all disabled:opacity-50 bg-slate-50/50 dark:bg-white/[0.02]">
                      <p className="font-semibold">v{version.version_number}</p>
                      <p className="text-[10px] text-slate-400">{new Date(version.created_at).toLocaleString()}</p>
                    </button>
                  ))}
                  {versions.length === 0 && <p className="text-xs text-slate-500">Aún sin versiones publicadas.</p>}
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-white/10">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Historial de Cambios</p>
                <div className="max-h-40 overflow-auto space-y-2 pr-1">
                  {publishLogs.map((entry) => {
                    const notes = typeof entry.metadata_json?.notes === "string" ? entry.metadata_json.notes : "";
                    return (
                      <div key={entry.id} className="rounded-lg border border-slate-200 dark:border-white/10 p-2 text-xs bg-slate-50/50 dark:bg-white/[0.02]">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-semibold uppercase tracking-wide text-[9px]">{entry.action}</p>
                          <p className="text-[9px] text-slate-400">{new Date(entry.created_at).toLocaleTimeString()}</p>
                        </div>
                        <p className="mt-0.5 text-[9px] text-slate-500">{entry.from_status || "sin estado"} &rarr; {entry.to_status || "sin estado"}</p>
                        {notes && <p className="mt-1 text-[9px] text-slate-400 line-clamp-2">{notes}</p>}
                      </div>
                    );
                  })}
                  {publishLogs.length === 0 && <p className="text-xs text-slate-500">Aun sin eventos de workflow.</p>}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: SEO ANALYZER */}
          {activeRightTab === "seo" && (
            <div className="space-y-4 animate-fade-in">
              <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Palabra Clave Objetivo</p>
                <input
                  value={seoKeyword}
                  onChange={(e) => setSeoKeyword(e.target.value)}
                  placeholder="Ej: jóvenes, adoración, testimonios"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />
                <p className="text-[9px] text-slate-400">Palabra clave principal para medir el SEO on-page.</p>
              </div>

              <div className="space-y-3 rounded-lg border border-slate-200 dark:border-white/10 p-4 bg-slate-50/50 dark:bg-white/[0.02]">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Puntaje SEO</p>
                  <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold text-white ${seoAnalysis.score >= 80 ? "bg-emerald-600" : seoAnalysis.score >= 50 ? "bg-amber-500" : "bg-red-500"}`}>
                    {seoAnalysis.score}%
                  </span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-white/10 h-2.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${seoAnalysis.score >= 80 ? "bg-emerald-500" : seoAnalysis.score >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                    style={{ width: `${seoAnalysis.score}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">
                  {seoAnalysis.score >= 80
                    ? "¡Excelente! Tu página cumple con los estándares óptimos de SEO on-page."
                    : seoAnalysis.score >= 50
                    ? "Aceptable. Considera añadir la palabra clave y mejorar las descripciones."
                    : "Crítico. Agrega título SEO, descripción y alt text para mejorar el ranking."}
                </p>
              </div>

              {/* READABILITY SCORE */}
              <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  <span>Legibilidad de Lectura</span>
                  <span className="text-emerald-500 font-bold">{readabilityScore.score}/100</span>
                </div>
                <p className="text-xs font-bold text-slate-800 dark:text-slate-200">{readabilityScore.label}</p>
                <p className="text-[9px] text-slate-400">Medido utilizando la densidad silábica y longitud de oraciones de las secciones activas.</p>
              </div>

              {/* SERP PREVIEW */}
              <div className="space-y-3 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Simulador SERP Google</p>
                  <div className="inline-flex rounded border border-slate-200 dark:border-white/10 overflow-hidden">
                    <button
                      onClick={() => setSerpPreviewDevice("desktop")}
                      className={`px-1.5 py-0.5 text-[8px] font-bold uppercase transition-all ${serpPreviewDevice === "desktop" ? "bg-primary text-white" : "bg-transparent text-slate-400"}`}
                    >
                      PC
                    </button>
                    <button
                      onClick={() => setSerpPreviewDevice("mobile")}
                      className={`px-1.5 py-0.5 text-[8px] font-bold uppercase transition-all ${serpPreviewDevice === "mobile" ? "bg-primary text-white" : "bg-transparent text-slate-400"}`}
                    >
                      Móvil
                    </button>
                  </div>
                </div>

                <div className={`rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-white text-black font-sans ${serpPreviewDevice === "mobile" ? "max-w-[280px]" : "w-full"}`}>
                  {serpPreviewDevice === "mobile" ? (
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5 text-xs text-[#202124]">
                        <span className="w-4 h-4 rounded-full bg-slate-200 flex items-center justify-center text-[8px] font-bold">⛪</span>
                        <div className="truncate text-left">{SITE_URL || siteKey} &rsaquo; {activeSlug || "slug"}</div>
                      </div>
                      <div className="text-base text-[#15c] hover:underline cursor-pointer font-medium leading-tight line-clamp-2 text-left">
                        {seoTitleDraft || activePage?.title || "Sin título SEO"}
                      </div>
                      <div className="text-xs text-[#3c4043] leading-relaxed line-clamp-3 text-left">
                        {seoDescriptionDraft || "Define una descripción para ver la vista previa social..."}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1 text-left">
                      <div className="text-[12px] text-[#202124] leading-none">
                        https://{SITE_URL || siteKey} &rsaquo; {activeSlug || "slug"}
                      </div>
                      <div className="text-lg text-[#1a0dab] hover:underline cursor-pointer font-normal leading-normal line-clamp-1">
                        {seoTitleDraft || activePage?.title || "Sin título SEO"}
                      </div>
                      <div className="text-[13px] text-[#4d5156] leading-relaxed line-clamp-2">
                        {seoDescriptionDraft || "Define una descripción para ver la vista previa social..."}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Recomendaciones SEO</p>
                <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                  {seoAnalysis.checks.map((check) => (
                    <div key={check.id} className="flex gap-2.5 items-start p-2 rounded-lg border border-slate-100 dark:border-white/5 bg-slate-50/30 dark:bg-white/[0.01]">
                      {check.type === "success" && <CheckCircle2 className="text-emerald-500 mt-0.5 shrink-0" size={14} />}
                      {check.type === "warning" && <AlertTriangle className="text-amber-500 mt-0.5 shrink-0" size={14} />}
                      {check.type === "error" && <XCircle className="text-red-500 mt-0.5 shrink-0" size={14} />}
                      <div>
                        <p className="text-xs font-bold text-slate-800 dark:text-slate-200">{check.label}</p>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">{check.tip}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: AI ASSISTANT (FAROGPT) */}
          {activeRightTab === "ai" && (
            <div className="space-y-4 animate-fade-in">
              <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">FaroGPT Asistente Editorial</p>
                
                <div className="space-y-3">
                  <div>
                    <label className="text-[9px] uppercase tracking-wide font-bold text-slate-400 block mb-1">Plantilla IA</label>
                    <select
                      value={aiTemplate}
                      onChange={(e) => setAiTemplate(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    >
                      <option value="aida">Fórmula AIDA (Atención-Interés-Deseo-Acción)</option>
                      <option value="pas">Fórmula PAS (Problema-Agitación-Solución)</option>
                      <option value="headlines">Titulares de Alto Impacto para Hero</option>
                      <option value="improve">Mejorar Texto / Optimizar Mensaje</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[9px] uppercase tracking-wide font-bold text-slate-400 block mb-1">Tono de Voz</label>
                    <select
                      value={aiTone}
                      onChange={(e) => setAiTone(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    >
                      <option value="warm">Cálido y Cercano (Comunidad)</option>
                      <option value="inspiration">Inspiracional y Profundo (Fe)</option>
                      <option value="formal">Respetuoso e Institucional (Iglesia)</option>
                      <option value="dynamic">Dinámico y Moderno (Jóvenes)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[9px] uppercase tracking-wide font-bold text-slate-400 block mb-1">Temática / Contexto</label>
                    <textarea
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder="Ej: Queremos invitar a las familias al pícnic de este domingo..."
                      className="w-full min-h-[64px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                </div>

                <button
                  onClick={handleAiGenerate}
                  disabled={aiGenerating || !aiPrompt.trim()}
                  className="w-full mt-3 rounded-lg bg-[hsl(var(--primary))] px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {aiGenerating ? (
                    <>
                      <RefreshCw size={12} className="animate-spin" /> FaroGPT redactando...
                    </>
                  ) : (
                    <>
                      <Wand2 size={12} /> Generar Contenido IA
                    </>
                  )}
                </button>
              </div>

              {aiOutput && (
                <div className="space-y-3 mt-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Resultado Generado</p>
                  <div className="p-3 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-white/5 text-[11px] font-mono max-h-[180px] overflow-y-auto whitespace-pre-wrap animate-fade-in">
                    {aiOutput}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={handleInsertAiAsSection}
                      className="rounded-lg bg-emerald-600 text-white px-2 py-1.5 text-[9px] font-semibold uppercase tracking-wide hover:bg-emerald-700 transition-all inline-flex items-center justify-center gap-1"
                    >
                      Insertar final
                    </button>
                    <button
                      onClick={handleReplaceActiveSectionWithAi}
                      disabled={!activeSectionId}
                      className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[9px] font-semibold uppercase tracking-wide hover:bg-slate-100 dark:hover:bg-white/5 transition-all inline-flex items-center justify-center gap-1 disabled:opacity-40"
                    >
                      Reemplazar activa
                    </button>
                  </div>
                </div>
              )}

              {/* MOCK AI IMAGE GENERATOR */}
              <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02] mt-3">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Generador de Imágenes IA</p>
                <input
                  value={aiImagePrompt}
                  onChange={(e) => setAiImagePrompt(e.target.value)}
                  placeholder="Ej: Jóvenes cantando, picnic de iglesia, Biblia..."
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs mb-2"
                />
                <button
                  onClick={handleAiImageGenerate}
                  disabled={aiImageGenerating || !aiImagePrompt.trim()}
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {aiImageGenerating ? (
                    <>
                      <RefreshCw size={12} className="animate-spin" /> Generando...
                    </>
                  ) : (
                    <>
                      <FileImage size={12} /> Generar Imagen Premium
                    </>
                  )}
                </button>

                {aiImageResult && (
                  <div className="space-y-2 mt-2 animate-fade-in">
                    <img src={aiImageResult} alt="Resultado IA" className="h-28 w-full object-cover rounded-lg border border-slate-200 dark:border-white/10" />
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => {
                          if (!activeSection) return;
                          const nextProps = { ...asObject(activeSection.props_json), image_url: aiImageResult };
                          updateSectionPropsLocal(nextProps);
                          saveSectionProps(nextProps);
                          setAiImageResult("");
                        }}
                        disabled={!activeSectionId}
                        className="rounded-lg bg-emerald-600 text-white px-2 py-1 text-[9px] font-semibold uppercase tracking-wide hover:bg-emerald-700 disabled:opacity-40"
                      >
                        Usar en Sección
                      </button>
                      <button
                        onClick={() => {
                          setSeoImageDraft(aiImageResult);
                          setAiImageResult("");
                        }}
                        className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-wide hover:bg-slate-100 dark:hover:bg-white/5"
                      >
                        Usar en SEO
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: METRICS & HEATMAP */}
          {activeRightTab === "analytics" && (
            <div className="space-y-4 animate-fade-in">
              {/* TIMEFRAME SELECTOR */}
              <div className="flex border border-slate-200 dark:border-white/10 rounded-lg overflow-hidden text-[9px] font-semibold uppercase tracking-wide">
                <button
                  onClick={() => setTimeframe("7d")}
                  className={`flex-1 py-1.5 text-center transition-all ${timeframe === "7d" ? "bg-primary text-white" : "bg-transparent text-slate-400"}`}
                >
                  7 días
                </button>
                <button
                  onClick={() => setTimeframe("30d")}
                  className={`flex-1 py-1.5 text-center transition-all border-x border-slate-200 dark:border-white/10 ${timeframe === "30d" ? "bg-primary text-white" : "bg-transparent text-slate-400"}`}
                >
                  30 días
                </button>
                <button
                  onClick={() => setTimeframe("all")}
                  className={`flex-1 py-1.5 text-center transition-all ${timeframe === "all" ? "bg-primary text-white" : "bg-transparent text-slate-400"}`}
                >
                  Histórico
                </button>
              </div>

              {/* DYNAMIC METRIC CARDS */}
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                  <p className="text-[8px] font-semibold uppercase tracking-wide text-slate-400">Visitas Totales</p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white mt-1">
                    {timeframe === "7d" ? "12,450" : timeframe === "30d" ? "54,230" : "423,910"}
                  </p>
                  <span className="text-[9px] font-bold text-emerald-600 inline-flex items-center gap-0.5 mt-1">
                    {timeframe === "7d" ? "▲ +12.4%" : timeframe === "30d" ? "▲ +18.7%" : "▲ +22.4%"}
                  </span>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                  <p className="text-[8px] font-semibold uppercase tracking-wide text-slate-400">Visitantes Únicos</p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white mt-1">
                    {timeframe === "7d" ? "4,820" : timeframe === "30d" ? "21,150" : "168,490"}
                  </p>
                  <span className="text-[9px] font-bold text-emerald-600 inline-flex items-center gap-0.5 mt-1">
                    {timeframe === "7d" ? "▲ +8.2%" : timeframe === "30d" ? "▲ +14.1%" : "▲ +19.6%"}
                  </span>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                  <p className="text-[8px] font-semibold uppercase tracking-wide text-slate-400">Tiempo Promedio</p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white mt-1">
                    {timeframe === "7d" ? "2m 45s" : timeframe === "30d" ? "3m 12s" : "2m 58s"}
                  </p>
                  <span className="text-[9px] font-bold text-emerald-600 inline-flex items-center gap-0.5 mt-1">▲ Óptimo</span>
                </div>
                <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                  <p className="text-[8px] font-semibold uppercase tracking-wide text-slate-400">Porcentaje Rebote</p>
                  <p className="text-lg font-bold text-slate-800 dark:text-white mt-1">
                    {timeframe === "7d" ? "42.1%" : timeframe === "30d" ? "39.8%" : "41.2%"}
                  </p>
                  <span className="text-[9px] font-bold text-emerald-600 inline-flex items-center gap-0.5 mt-1">● Saludable</span>
                </div>
              </div>

              {/* AB TESTING SIMULATOR */}
              <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02] space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 font-bold text-primary">Test A/B Integrado</p>
                  <button
                    onClick={() => setAbTestingActive(!abTestingActive)}
                    className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase transition-all ${abTestingActive ? "bg-emerald-600 text-white animate-pulse" : "bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-slate-300"}`}
                  >
                    {abTestingActive ? "Activo" : "Inactivo"}
                  </button>
                </div>
                
                {abTestingActive ? (
                  <div className="space-y-2.5 animate-fade-in text-[10px]">
                    <div className="space-y-1">
                      <div className="flex justify-between text-slate-400">
                        <span>Tráfico Variante A (Original)</span>
                        <span className="font-bold">{100 - abTrafficSplit}%</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Tráfico Variante B (Alternativa)</span>
                        <span className="font-bold">{abTrafficSplit}%</span>
                      </div>
                      <input
                        type="range"
                        min="10"
                        max="90"
                        value={abTrafficSplit}
                        onChange={(e) => setAbTrafficSplit(Number(e.target.value))}
                        className="w-full accent-primary h-1 bg-slate-200 dark:bg-white/10 rounded-lg cursor-pointer"
                      />
                    </div>

                    <div className="rounded border p-2 bg-slate-100/40 dark:bg-white/[0.01] space-y-1">
                      <p className="font-bold uppercase tracking-wider text-[8px] text-slate-400">Simulación de Conversión</p>
                      <div className="flex justify-between">
                        <span>Conversión Variante A:</span>
                        <span className="font-mono">3.2%</span>
                      </div>
                      <div className="flex justify-between text-emerald-500 font-bold">
                        <span>Conversión Variante B:</span>
                        <span className="font-mono">4.9% (▲ +53%)</span>
                      </div>
                      <p className="text-[8px] text-slate-400 mt-1">Confianza estadística: <strong className="text-emerald-500 font-bold">97.4%</strong> (Resultado Significativo)</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-[9px] text-slate-400">WordPress requiere plugins complejos para test A/B. Activa esta opción para diseñar variantes y dividir el tráfico automáticamente.</p>
                )}
              </div>

              {/* HEATMAP / LIVE CLICK MAP */}
              <div className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02] space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 font-bold">Mapa de Calor (Live)</p>
                  <button
                    onClick={() => setShowHeatmap(!showHeatmap)}
                    className={`px-3 py-1 rounded-md text-[9px] font-semibold uppercase tracking-wide transition-all ${showHeatmap ? "bg-red-500 text-white animate-pulse" : "bg-slate-200 dark:bg-white/10 text-slate-600 dark:text-slate-300"}`}
                  >
                    {showHeatmap ? "Ver Activo" : "Activar"}
                  </button>
                </div>

                {showHeatmap && (
                  <div className="space-y-2 animate-fade-in">
                    <label className="text-[9px] uppercase tracking-wide font-bold text-slate-400 block mb-1">Tipo de Visualización</label>
                    <div className="flex rounded border border-slate-200 dark:border-white/10 overflow-hidden text-[9px] font-bold text-center">
                      <button
                        onClick={() => setHeatmapType("clicks")}
                        className={`flex-1 py-1 transition-all ${heatmapType === "clicks" ? "bg-primary text-white" : "bg-transparent text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5"}`}
                      >
                        Clics
                      </button>
                      <button
                        onClick={() => setHeatmapType("scroll")}
                        className={`flex-1 py-1 transition-all border-x border-slate-200 dark:border-white/10 ${heatmapType === "scroll" ? "bg-primary text-white" : "bg-transparent text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5"}`}
                      >
                        Scroll
                      </button>
                      <button
                        onClick={() => setHeatmapType("attention")}
                        className={`flex-1 py-1 transition-all ${heatmapType === "attention" ? "bg-primary text-white" : "bg-transparent text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5"}`}
                      >
                        Atención
                      </button>
                    </div>
                  </div>
                )}
                
                <p className="text-[9px] text-slate-400">Representación visual interactiva en tiempo real sobre el canvas del comportamiento del usuario.</p>
              </div>
            </div>
          )}

          {/* Section Inspector (renders below tabs if activeSection is set) */}
          <div className="space-y-2 pt-4 border-t border-slate-200 dark:border-white/10">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 font-bold">Inspector sección</p>
            {!activeSection ? (
              <p className="text-xs text-slate-500">Selecciona una sección del canvas.</p>
            ) : (
              <fieldset disabled={!canEdit} className="space-y-2.5 disabled:opacity-60">
                <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{activeSection.type}</p>
                <input
                  value={safeString(activeSection.props_json?.title)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("title", e.target.value)}
                  placeholder="Título"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />
                <textarea
                  value={safeString(activeSection.props_json?.body)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), body: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("body", e.target.value)}
                  placeholder="Contenido"
                  className="w-full min-h-[90px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />
                <input
                  value={safeString(activeSection.props_json?.cta_label)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), cta_label: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("cta_label", e.target.value)}
                  placeholder="Texto CTA"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />
                <input
                  value={safeString(activeSection.props_json?.cta_href)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), cta_href: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("cta_href", e.target.value)}
                  placeholder="URL CTA"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />

                {(activeSection.type === "hero" || activeSection.type === "gallery") && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                      {activeSection.type === "hero" ? "Imagen hero" : "Imagen de galeria"}
                    </p>
                    {safeString(activeSection.props_json?.image_url) ? (
                      <div className="overflow-hidden rounded-md border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5">
                        <img src={safeString(activeSection.props_json?.image_url)} alt={safeString(activeSection.props_json?.image_alt) || "Imagen seleccionada"} className="h-28 w-full object-cover" />
                      </div>
                    ) : (
                      <div className="rounded-md border border-dashed border-slate-300 dark:border-white/20 bg-slate-50 dark:bg-white/5 p-4 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">
                        Sin imagen seleccionada
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        setMediaPickerTarget("section");
                        setMediaPickerOpen(true);
                      }}
                      className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2"
                    >
                      <ImageIcon size={13} /> Elegir de media
                    </button>
                    <input
                      value={safeString(activeSection.props_json?.image_url)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), image_url: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("image_url", e.target.value)}
                      placeholder="URL manual de imagen"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      value={safeString(activeSection.props_json?.image_alt)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), image_alt: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("image_alt", e.target.value)}
                      placeholder="Texto alternativo"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "embed" && (
                  <input
                    value={safeString(activeSection.props_json?.embed_url)}
                    onChange={(e) => {
                      const nextProps = { ...asObject(activeSection.props_json), embed_url: e.target.value };
                      updateSectionPropsLocal(nextProps);
                    }}
                    onBlur={(e) => saveSectionField("embed_url", e.target.value)}
                    placeholder="URL embed (YouTube, Vimeo, etc.)"
                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                  />
                )}

                {activeSection.type === "cards" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Items de tarjetas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                      <div key={`card-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                        {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-700">Archivado</p>}
                        <input
                          value={safeString(itemObject.title)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { title: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { title: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Título tarjeta"
                          className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <textarea
                          value={safeString(itemObject.body)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { body: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { body: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Descripción tarjeta"
                          className="w-full min-h-[64px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <input
                          value={safeString(itemObject.icon)}
                          onChange={(e) => upsertArrayItem("items", index, { icon: e.target.value })}
                          onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { icon: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                          placeholder="Icono emoji (ej: 🎯)"
                          className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <input
                          value={safeString(itemObject.href)}
                          onChange={(e) => upsertArrayItem("items", index, { href: e.target.value })}
                          onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { href: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                          placeholder="URL (opcional, hace la tarjeta clicable)"
                          className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <button
                          onClick={() => {
                            const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}
                        >
                          {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                          {isItemArchived ? "Restaurar" : "Archivar"}
                        </button>
                      </div>
                      );
                    })}
                    <button
                      onClick={() => {
                        const nextProps = addArrayItem("items", { title: "Nueva tarjeta", body: "Descripción", status: "published" });
                        if (nextProps) saveSectionProps(nextProps);
                      }}
                      className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide"
                    >
                      + Añadir tarjeta
                    </button>
                  </div>
                )}

                {activeSection.type === "faq" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Preguntas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                      <div key={`faq-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                        {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-700">Archivado</p>}
                        <input
                          value={safeString(itemObject.q)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { q: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { q: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Pregunta"
                          className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <textarea
                          value={safeString(itemObject.a)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { a: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { a: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Respuesta"
                          className="w-full min-h-[64px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <button
                          onClick={() => {
                            const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}
                        >
                          {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                          {isItemArchived ? "Restaurar" : "Archivar"}
                        </button>
                      </div>
                      );
                    })}
                    <button
                      onClick={() => {
                        const nextProps = addArrayItem("items", { q: "Nueva pregunta", a: "Respuesta", status: "published" });
                        if (nextProps) saveSectionProps(nextProps);
                      }}
                      className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide"
                    >
                      + Añadir pregunta
                    </button>
                  </div>
                )}

                {activeSection.type === "video_hero" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Video de fondo</p>
                    <input
                      value={safeString(activeSection.props_json?.video_url)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), video_url: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("video_url", e.target.value)}
                      placeholder="URL del video"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "rich_text_columns" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Segunda columna</p>
                    <textarea
                      value={safeString(activeSection.props_json?.body_2)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), body_2: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("body_2", e.target.value)}
                      placeholder="Contenido de la segunda columna"
                      className="w-full min-h-12 rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "countdown" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Fecha objetivo</p>
                    <input
                      type="datetime-local"
                      value={safeString(activeSection.props_json?.target_date).slice(0, 16)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), target_date: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("target_date", e.target.value)}
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "popup_banner" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Pop-up</p>
                    <input
                      type="number"
                      value={safeString(activeSection.props_json?.delay_ms) || "2000"}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), delay_ms: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("delay_ms", e.target.value)}
                      placeholder="Retraso en milisegundos"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      type="datetime-local"
                      value={safeString(activeSection.props_json?.start_at).slice(0, 16)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), start_at: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("start_at", e.target.value)}
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      type="datetime-local"
                      value={safeString(activeSection.props_json?.end_at).slice(0, 16)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), end_at: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("end_at", e.target.value)}
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <textarea
                      value={Array.isArray(activeSection.props_json?.show_on_paths) ? activeSection.props_json.show_on_paths.join("\n") : safeString(activeSection.props_json?.show_on_paths)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), show_on_paths: e.target.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean) };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionProps({ ...asObject(activeSection.props_json), show_on_paths: e.target.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean) })}
                      placeholder="/\n/nosotros\n/cursos"
                      className="w-full min-h-16 rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <textarea
                      value={Array.isArray(activeSection.props_json?.hide_on_paths) ? activeSection.props_json.hide_on_paths.join("\n") : safeString(activeSection.props_json?.hide_on_paths)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), hide_on_paths: e.target.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean) };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionProps({ ...asObject(activeSection.props_json), hide_on_paths: e.target.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean) })}
                      placeholder="/login\n/checkout"
                      className="w-full min-h-16 rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <select
                      value={safeString(activeSection.props_json?.dismiss_mode) || "local"}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), dismiss_mode: e.target.value };
                        updateSectionPropsLocal(nextProps);
                        saveSectionField("dismiss_mode", e.target.value);
                      }}
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    >
                      <option value="local">Persistente (localStorage)</option>
                      <option value="session">Solo sesión</option>
                      <option value="none">Sin persistencia</option>
                    </select>
                    <input
                      type="number"
                      value={safeString(activeSection.props_json?.dismiss_days) || "30"}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), dismiss_days: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("dismiss_days", e.target.value)}
                      placeholder="Duración del cierre en días"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      value={safeString(activeSection.props_json?.dismiss_key)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), dismiss_key: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("dismiss_key", e.target.value)}
                      placeholder="Clave de cierre personalizada (opcional)"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "stats" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Metricas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`stat-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-700">Archivado</p>}
                          <input value={safeString(itemObject.value)} onChange={(e) => upsertArrayItem("items", index, { value: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { value: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Valor: 10K+" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.label)} onChange={(e) => upsertArrayItem("items", index, { label: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { label: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Etiqueta" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { value: "0", label: "Nueva metrica", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir metrica
                    </button>
                  </div>
                )}

                {activeSection.type === "team" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Equipo</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`team-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-700">Archivado</p>}
                          <input value={safeString(itemObject.name)} onChange={(e) => upsertArrayItem("items", index, { name: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { name: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Nombre" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.role)} onChange={(e) => upsertArrayItem("items", index, { role: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { role: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Rol" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.image)} onChange={(e) => upsertArrayItem("items", index, { image: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { image: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL imagen" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar persona" : "Archivar persona"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { name: "Nombre", role: "Rol", image: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir persona
                    </button>
                  </div>
                )}

                {activeSection.type === "pricing" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Planes / donaciones</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`pricing-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-700">Archivado</p>}
                          <input value={safeString(itemObject.name)} onChange={(e) => upsertArrayItem("items", index, { name: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { name: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Nombre del plan" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.price)} onChange={(e) => upsertArrayItem("items", index, { price: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { price: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Precio" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.features)} onChange={(e) => upsertArrayItem("items", index, { features: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { features: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Beneficios, uno por linea" className="w-full min-h-[64px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.btn)} onChange={(e) => upsertArrayItem("items", index, { btn: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { btn: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Texto del boton" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.btn_href)} onChange={(e) => upsertArrayItem("items", index, { btn_href: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { btn_href: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL del boton (opcional)" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <label className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                            <input type="checkbox" checked={safeString(itemObject.featured) === "true"} onChange={(e) => { const nextProps = upsertArrayItem("items", index, { featured: String(e.target.checked) }); if (nextProps) saveSectionProps(nextProps); }} />
                            Destacado (featured)
                          </label>
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar plan" : "Archivar plan"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { name: "Nuevo plan", price: "$0", features: "Beneficio", btn: "Seleccionar", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir plan
                    </button>
                  </div>
                )}

                {activeSection.type === "gallery" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Imágenes de galería (items)</p>
                    <p className="text-[9px] text-slate-400">Si agregas items aquí se usa galería múltiple; si no, se usa la imagen hero de arriba.</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`gallery-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-700">Archivado</p>}
                          {safeString(itemObject.url) && <img src={safeString(itemObject.url)} alt={safeString(itemObject.alt)} className="w-full h-20 object-cover rounded-md" />}
                          <input value={safeString(itemObject.url)} onChange={(e) => upsertArrayItem("items", index, { url: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { url: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL de imagen" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.alt)} onChange={(e) => upsertArrayItem("items", index, { alt: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { alt: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Alt text" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.caption)} onChange={(e) => upsertArrayItem("items", index, { caption: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { caption: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Leyenda (opcional)" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { url: "", alt: "", caption: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir imagen
                    </button>
                  </div>
                )}

                {activeSection.type === "image_text" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Imagen + Texto</p>
                    <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Imagen</p>
                      {safeString(activeSection.props_json?.image_url) && (
                        <img src={safeString(activeSection.props_json?.image_url)} alt="" className="w-full h-24 object-cover rounded-md" />
                      )}
                      <button type="button" onClick={() => { setMediaPickerTarget("section"); setMediaPickerOpen(true); }} className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2">
                        <ImageIcon size={13} /> Elegir imagen
                      </button>
                      <input value={safeString(activeSection.props_json?.image_url)} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), image_url: e.target.value }; updateSectionPropsLocal(nextProps); }} onBlur={(e) => saveSectionField("image_url", e.target.value)} placeholder="URL manual" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs" />
                      <input value={safeString(activeSection.props_json?.image_alt)} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), image_alt: e.target.value }; updateSectionPropsLocal(nextProps); }} onBlur={(e) => saveSectionField("image_alt", e.target.value)} placeholder="Alt text" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs" />
                    </div>
                    <select value={safeString(activeSection.props_json?.image_side) || "right"} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), image_side: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("image_side", e.target.value); }} className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs">
                      <option value="right">Imagen a la derecha</option>
                      <option value="left">Imagen a la izquierda</option>
                    </select>
                  </div>
                )}

                {activeSection.type === "timeline" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Hitos de línea de tiempo</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`timeline-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-700">Archivado</p>}
                          <input value={safeString(itemObject.year)} onChange={(e) => upsertArrayItem("items", index, { year: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { year: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Año o etiqueta (ej: 2020)" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.title)} onChange={(e) => upsertArrayItem("items", index, { title: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { title: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Título del hito" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.body)} onChange={(e) => upsertArrayItem("items", index, { body: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { body: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Descripción" className="w-full min-h-[48px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar hito" : "Archivar hito"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { year: "2024", title: "Nuevo hito", body: "Descripción", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir hito
                    </button>
                  </div>
                )}

                {activeSection.type === "icon_grid" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Items del grid</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`icon-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-700">Archivado</p>}
                          <input value={safeString(itemObject.icon)} onChange={(e) => upsertArrayItem("items", index, { icon: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { icon: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Emoji icono (ej: 🎯)" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.title)} onChange={(e) => upsertArrayItem("items", index, { title: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { title: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Título" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.body)} onChange={(e) => upsertArrayItem("items", index, { body: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { body: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Descripción breve" className="w-full min-h-[48px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { icon: "✨", title: "Nuevo item", body: "Descripción", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir item
                    </button>
                  </div>
                )}

                {activeSection.type === "newsletter" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Suscripción Email</p>
                    <input
                      value={safeString(activeSection.props_json?.action_url)}
                      onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), action_url: e.target.value }; updateSectionPropsLocal(nextProps); }}
                      onBlur={(e) => saveSectionField("action_url", e.target.value)}
                      placeholder="URL de acción (POST con {name, email})"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "cta_banner" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Segundo botón (opcional)</p>
                    <input
                      value={safeString(activeSection.props_json?.cta_label_2)}
                      onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), cta_label_2: e.target.value }; updateSectionPropsLocal(nextProps); }}
                      onBlur={(e) => saveSectionField("cta_label_2", e.target.value)}
                      placeholder="Texto segundo botón"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      value={safeString(activeSection.props_json?.cta_href_2)}
                      onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), cta_href_2: e.target.value }; updateSectionPropsLocal(nextProps); }}
                      onBlur={(e) => saveSectionField("cta_href_2", e.target.value)}
                      placeholder="URL segundo botón"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "testimonials" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Testimonios manuales de esta seccion</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`manual-testimonial-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-700">Archivado</p>}
                          <input value={safeString(itemObject.author)} onChange={(e) => upsertArrayItem("items", index, { author: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { author: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Autor" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.role)} onChange={(e) => upsertArrayItem("items", index, { role: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { role: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Rol" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.content)} onChange={(e) => upsertArrayItem("items", index, { content: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { content: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Contenido" className="w-full min-h-[64px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <select value={safeString(itemObject.stars) || "5"} onChange={(e) => { const nextProps = upsertArrayItem("items", index, { stars: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs">
                            <option value="5">★★★★★ 5 estrellas</option>
                            <option value="4">★★★★☆ 4 estrellas</option>
                            <option value="3">★★★☆☆ 3 estrellas</option>
                          </select>
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { author: "Autor", role: "Rol", content: "Testimonio", stars: "5", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir testimonio
                    </button>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => setSectionVisibility(!activeSection.is_visible)} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1">
                    {activeSection.is_visible ? <EyeOff size={11} /> : <Eye size={11} />} {activeSection.is_visible ? "Ocultar" : "Mostrar"}
                  </button>
                  <button onClick={duplicateSection} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1">
                    <Copy size={11} /> Duplicar
                  </button>
                  <button onClick={toggleSectionArchive} className={`col-span-2 rounded-lg border px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 ${activeSection.status === "archived" ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}>
                    {activeSection.status === "archived" ? <RotateCcw size={11} /> : <Archive size={11} />}
                    {activeSection.status === "archived" ? "Restaurar seccion" : "Archivar seccion"}
                  </button>
                </div>
                <p className="text-[10px] text-slate-400">{saving ? "Guardando..." : "Cambios guardados al salir del campo"}</p>
              </fieldset>
            )}
          </div>
        </aside>
      </div>
      <MediaPicker
        open={mediaPickerOpen}
        token={token}
        selectedUrl={mediaPickerTarget === "seo" ? seoImageDraft : safeString(activeSection?.props_json?.image_url)}
        onClose={() => setMediaPickerOpen(false)}
        onSelect={(item) => {
          if (mediaPickerTarget === "seo") {
            setSeoImageDraft(item.url);
            setMediaPickerOpen(false);
            return;
          }
          if (!activeSection) return;
          const nextProps = {
            ...asObject(activeSection.props_json),
            image_url: item.url,
            image_alt: item.alt_text || item.filename || "",
            media_id: item.id,
          };
          updateSectionPropsLocal(nextProps);
          saveSectionProps(nextProps);
          setMediaPickerOpen(false);
        }}
      />
    </div>
  );
}
