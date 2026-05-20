"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Archive, ArrowDown, ArrowUp, Check, Copy, Eye, EyeOff, ExternalLink, FileImage, ImageIcon, LayoutPanelTop, Monitor, Plus, RotateCcw, Save, Search, Send, Smartphone, Upload, Undo2, X } from "lucide-react";
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

const SECTION_TYPES = [
  "hero", "video_hero", "rich_text", "rich_text_columns",
  "cards", "cta_banner", "gallery", "faq", "embed",
  "testimonials", "stats", "team", "countdown", "pricing", "popup_banner"
];

const SECTION_TYPE_COLORS: Record<string, string> = {
  hero:              "bg-blue-600",
  video_hero:        "bg-indigo-600",
  rich_text:         "bg-slate-500",
  rich_text_columns: "bg-slate-600",
  cards:             "bg-blue-600",
  cta_banner:        "bg-emerald-600",
  gallery:           "bg-pink-500",
  faq:               "bg-amber-500",
  embed:             "bg-cyan-600",
  testimonials:      "bg-rose-500",
  stats:             "bg-teal-600",
  team:              "bg-orange-500",
  countdown:         "bg-red-600",
  pricing:           "bg-sky-600",
  popup_banner:      "bg-fuchsia-500",
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
  popup_banner:      "Pop-up Promocional",
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
          cta_href: "/faro/nosotros",
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
          cta_href: "/faro/conocer-a-jesus",
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
      cta_href: "/faro/conocer-a-jesus",
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
      body: "Conoce nuestros próximos eventos y Faros en Casa.",
      cta_label: "Ver eventos",
      cta_href: "/faro/eventos",
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

function SectionPreview({ section }: { section: CmsSection }) {
  const title = safeString(section.props_json?.title);
  const body = safeString(section.props_json?.body);
  const imageUrl = safeString(section.props_json?.image_url);
  const ctaLabel = safeString(section.props_json?.cta_label);
  const typeColor = SECTION_TYPE_COLORS[section.type] ?? "bg-slate-500";
  const typeLabel = SECTION_TYPE_LABEL[section.type] ?? section.type;

  const TypeBadge = () => (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-black uppercase tracking-widest text-white ${typeColor}`}>
      {typeLabel}
    </span>
  );

  if (section.type === "hero" || section.type === "video_hero") {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 dark:border-white/20 p-4 space-y-2">
        <TypeBadge />
        <h3 className="text-lg font-black text-slate-900 dark:text-white leading-tight">{title || "Título hero"}</h3>
        <p className="text-sm text-slate-500 line-clamp-2">{body || "Subtítulo o descripción principal"}</p>
        {ctaLabel && <span className="inline-block mt-1 px-3 py-1 bg-blue-600 text-white rounded-lg text-[10px] font-black uppercase">{ctaLabel}</span>}
        {section.type === "video_hero" && <p className="text-[9px] text-slate-400 font-bold uppercase">🎬 Video de fondo configurado</p>}
      </div>
    );
  }
  if (section.type === "cards" || section.type === "pricing") {
    const items = Array.isArray(section.props_json?.items)
      ? (section.props_json.items as Array<Record<string,unknown>>).filter((item) => item.status !== "archived")
      : [];
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 dark:border-white/20 p-4 space-y-2">
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
      <div className="rounded-2xl border border-dashed border-slate-300 dark:border-white/20 p-4 space-y-2">
        <TypeBadge />
        {imageUrl
          // eslint-disable-next-line @next/next/no-img-element
          ? <img src={imageUrl} alt="gallery" className="w-full h-24 object-cover rounded-xl" />
          : <div className="w-full h-16 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-[9px] text-slate-400 font-bold uppercase">Sin imagen configurada</div>
        }
      </div>
    );
  }
  if (section.type === "cta_banner") {
    return (
      <div className="rounded-2xl border border-dashed border-emerald-300 dark:border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-900/10 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-black text-slate-800 dark:text-slate-100">{title || "Llamado a la Acción"}</p>
        <p className="text-xs text-slate-500 line-clamp-1">{body || "Subtítulo"}</p>
        {ctaLabel && <span className="inline-block px-3 py-1 bg-emerald-600 text-white rounded-lg text-[10px] font-black uppercase">{ctaLabel}</span>}
      </div>
    );
  }
  if (section.type === "testimonials") {
    return (
      <div className="rounded-2xl border border-dashed border-rose-300 dark:border-rose-500/30 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{title || "Sección de Testimonios"}</p>
        <div className="flex gap-2">
          {[1,2,3].map(i => (
            <div key={i} className="flex-1 h-8 rounded-xl bg-slate-100 dark:bg-white/5 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }
  if (section.type === "stats") {
    const stats = Array.isArray(section.props_json?.items) ? section.props_json.items as Array<Record<string,unknown>> : [];
    return (
      <div className="rounded-2xl border border-dashed border-teal-300 dark:border-teal-500/30 p-4 space-y-2">
        <TypeBadge />
        <div className="grid grid-cols-3 gap-2">
          {(stats.length > 0 ? stats : [{value: "—", label: "Métrica"}]).slice(0,3).map((s, i) => (
            <div key={i} className="text-center">
              <p className="text-base font-black text-teal-600">{safeString(s.value) || "—"}</p>
              <p className="text-[9px] text-slate-400 font-bold uppercase">{safeString(s.label) || "Métrica"}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (section.type === "team") {
    return (
      <div className="rounded-2xl border border-dashed border-orange-300 dark:border-orange-500/30 p-4 space-y-2">
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
      <div className="rounded-2xl border border-dashed border-red-300 dark:border-red-500/30 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{title || "Cuenta Regresiva"}</p>
        <div className="flex gap-3">
          {["DD", "HH", "MM", "SS"].map(u => (
            <div key={u} className="text-center">
              <div className="size-10 rounded-xl bg-red-600 flex items-center justify-center text-white font-black text-sm">00</div>
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
      <div className="rounded-2xl border border-dashed border-amber-300 dark:border-amber-500/30 p-4 space-y-2">
        <TypeBadge />
        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{title || "Preguntas Frecuentes"}</p>
        {faqs.slice(0,2).map((f, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className="text-amber-500 font-black mt-0.5">Q</span>
            <span className="text-slate-600 dark:text-slate-300 line-clamp-1">{safeString(f.q) || "Pregunta"}</span>
          </div>
        ))}
      </div>
    );
  }
  if (section.type === "embed") {
    const embedUrl = safeString(section.props_json?.embed_url);
    return (
      <div className="rounded-2xl border border-dashed border-cyan-300 dark:border-cyan-500/30 p-4 space-y-2">
        <TypeBadge />
        {embedUrl
          ? <p className="text-[10px] text-slate-500 font-mono truncate">{embedUrl}</p>
          : <div className="w-full h-12 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-[9px] text-slate-400 font-bold uppercase">Sin URL configurada</div>
        }
      </div>
    );
  }
  // rich_text, rich_text_columns, default
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 dark:border-white/20 p-4 space-y-2">
      <TypeBadge />
      <h4 className="text-base font-black text-slate-800 dark:text-slate-100">{title || "Título"}</h4>
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
      const created = await apiFetch<CmsMediaItem>("/cms/media/upload", {
        method: "POST",
        token,
        query: { section: "builder", alt_text: file.name },
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
      <div className="w-full max-w-5xl max-h-[86vh] overflow-hidden rounded-2xl bg-white dark:bg-[#111418] border border-slate-200 dark:border-white/10 shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/10 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-300 flex items-center justify-center">
              <ImageIcon size={18} />
            </div>
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Biblioteca CMS</p>
              <h2 className="text-base font-black text-slate-900 dark:text-white">Seleccionar imagen</h2>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10">
            <X size={18} />
          </button>
        </div>

        <div className="flex items-center gap-3 border-b border-slate-200 dark:border-white/10 px-5 py-3">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por archivo, alt text o seccion"
              className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
            />
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white disabled:opacity-50">
            <Upload size={14} />
            {uploading ? "Subiendo..." : "Subir imagen"}
            <input type="file" accept="image/*" className="hidden" onChange={uploadImage} disabled={uploading} />
          </label>
        </div>

        <div className="max-h-[62vh] overflow-y-auto p-5">
          {loading ? (
            <div className="py-16 text-center text-sm font-bold text-slate-400">Cargando biblioteca...</div>
          ) : filtered.length === 0 ? (
            <div className="py-16 text-center">
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
                    className={`group text-left rounded-2xl border overflow-hidden bg-white dark:bg-white/[0.03] transition-all ${isSelected ? "border-blue-500 ring-2 ring-blue-500/20" : "border-slate-200 dark:border-white/10 hover:border-blue-300"}`}
                  >
                    <div className="relative aspect-video bg-slate-100 dark:bg-white/5">
                      <img src={item.url} alt={item.alt_text || item.filename || ""} className="h-full w-full object-cover" />
                      {isSelected && (
                        <span className="absolute right-2 top-2 size-7 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-lg">
                          <Check size={15} />
                        </span>
                      )}
                    </div>
                    <div className="p-3">
                      <p className="truncate text-xs font-black text-slate-800 dark:text-slate-100">{item.filename || "Imagen CMS"}</p>
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
  const [siteKey, setSiteKey] = useState("faro");
  const [sites, setSites] = useState<Array<{ site_key: string; name: string; base_path: string }>>([]);
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [activeSlug, setActiveSlug] = useState("");
  const [sections, setSections] = useState<CmsSection[]>([]);
  const [versions, setVersions] = useState<CmsPageVersion[]>([]);
  const [publishLogs, setPublishLogs] = useState<CmsPublishLog[]>([]);
  const [newPageTitle, setNewPageTitle] = useState("");
  const [newSectionType, setNewSectionType] = useState("rich_text");
  const [pageTemplateKey, setPageTemplateKey] = useState("simple");
  const [activeSectionId, setActiveSectionId] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [draggedSectionId, setDraggedSectionId] = useState<number | null>(null);
  const [previewDevice, setPreviewDevice] = useState<"desktop" | "mobile">("desktop");
  const [rawPropsDraft, setRawPropsDraft] = useState("");
  const [rawPropsError, setRawPropsError] = useState<string | null>(null);
  const [pageTitleDraft, setPageTitleDraft] = useState("");
  const [pageSlugDraft, setPageSlugDraft] = useState("");
  const [seoTitleDraft, setSeoTitleDraft] = useState("");
  const [seoDescriptionDraft, setSeoDescriptionDraft] = useState("");
  const [seoImageDraft, setSeoImageDraft] = useState("");
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const [mediaPickerTarget, setMediaPickerTarget] = useState<"section" | "seo">("section");

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
    if (!activeSection) {
      setRawPropsDraft("");
      setRawPropsError(null);
      return;
    }
    setRawPropsDraft(JSON.stringify(activeSection.props_json ?? {}, null, 2));
    setRawPropsError(null);
  }, [activeSection]);

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

  const removeArrayItem = (key: "items", index: number) => {
    if (!activeSection) return;
    const currentProps = asObject(activeSection.props_json);
    const currentItems = Array.isArray(currentProps[key]) ? [...(currentProps[key] as Array<Record<string, unknown>>)] : [];
    const nextItems = currentItems.filter((_, i) => i !== index);
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

  const moveSection = async (sectionId: number, direction: "up" | "down") => {
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

  const moveSectionToIndex = async (sourceId: number, targetId: number) => {
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

  const rollback = async (versionId: number) => {
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
    <div className="space-y-6 p-6">
      <div className="rounded-3xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-6 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">CMS V2 Builder</p>
          <h1 className="mt-2 text-2xl font-black">Constructor visual multisitio</h1>
        </div>
        <div className="rounded-xl bg-primary/10 px-3 py-2 text-primary text-xs font-black uppercase tracking-widest inline-flex items-center gap-2">
          <LayoutPanelTop size={14} /> Beta
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <aside className="lg:col-span-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-3">
          <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Sitio</label>
          <select value={siteKey} onChange={(e) => setSiteKey(e.target.value)} className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm">
            {sites.length === 0 && <option value="faro">faro</option>}
            {sites.map((site) => (
              <option key={site.site_key} value={site.site_key}>{site.name} ({site.site_key})</option>
            ))}
          </select>

          <div className="rounded-xl border border-slate-200 dark:border-white/10 p-3 space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Nueva página</p>
            <input value={newPageTitle} onChange={(e) => setNewPageTitle(e.target.value)} placeholder="Ej: Página de bienvenida" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm" disabled={!canEdit} />
            <button onClick={createPage} disabled={!canEdit} className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-[10px] font-black uppercase tracking-widest text-white disabled:opacity-50"><Plus size={12} /> Crear vacía</button>
            <select value={pageTemplateKey} onChange={(e) => setPageTemplateKey(e.target.value)} className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs">
              {PAGE_TEMPLATES.map((template) => (
                <option key={template.key} value={template.key}>{template.label}</option>
              ))}
            </select>
            <button onClick={createPageFromTemplate} disabled={!canEdit} className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest disabled:opacity-50">
              <Plus size={12} /> Crear con plantilla
            </button>
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Páginas</p>
            {pages.map((page) => (
              <button key={page.id} onClick={() => setActiveSlug(page.slug)} className={`w-full text-left rounded-lg border px-3 py-2 text-sm ${activeSlug === page.slug ? "border-primary/40 bg-primary/5" : "border-slate-200 dark:border-white/10"}`}>
                <p className="font-bold">{page.title}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-400">/{page.slug} · {page.status}</p>
              </button>
            ))}
          </div>

          <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-white/10">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Plantillas rápidas</p>
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

        <section className="lg:col-span-6 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-lg font-black">Canvas · {activeSlug ? `/${activeSlug}` : "Selecciona página"}</h2>
            <div className="flex items-center gap-2">
              <div className="inline-flex rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden">
                <button
                  onClick={() => setPreviewDevice("desktop")}
                  className={`px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center gap-1 ${previewDevice === "desktop" ? "bg-primary text-white" : "bg-transparent"}`}
                >
                  <Monitor size={11} /> Desktop
                </button>
                <button
                  onClick={() => setPreviewDevice("mobile")}
                  className={`px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center gap-1 ${previewDevice === "mobile" ? "bg-primary text-white" : "bg-transparent"}`}
                >
                  <Smartphone size={11} /> Mobile
                </button>
              </div>
              <select value={newSectionType} onChange={(e) => setNewSectionType(e.target.value)} className="rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm">
                {SECTION_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
              <button onClick={addSection} disabled={!activeSlug || !canEdit} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest disabled:opacity-50">
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
                className={`rounded-xl border p-3 cursor-grab active:cursor-grabbing ${section.status === "archived" ? "opacity-70 border-amber-200 bg-amber-50/40 dark:bg-amber-500/5" : section.id === activeSectionId ? "border-primary/40 bg-primary/5" : "border-slate-200 dark:border-white/10"}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <button onClick={() => setActiveSectionId(section.id)} className="text-left">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                      {section.type} {section.status === "archived" ? "· archivada" : ""}
                    </p>
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{safeString(section.props_json?.title) || "Sección"}</p>
                  </button>
                  <div className="flex items-center gap-1">
                    <button onClick={() => moveSection(section.id, "up")} disabled={!canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 p-1.5 disabled:opacity-50"><ArrowUp size={12} /></button>
                    <button onClick={() => moveSection(section.id, "down")} disabled={!canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 p-1.5 disabled:opacity-50"><ArrowDown size={12} /></button>
                  </div>
                </div>
                <div className="mt-3">
                  <SectionPreview section={section} />
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
                className="rounded-xl border border-dashed border-slate-300 dark:border-white/20 p-3 text-center text-[10px] font-black uppercase tracking-widest text-slate-400"
              >
                Soltar aquí para mover al final
              </div>
            )}
          </div>
        </section>

        <aside className="lg:col-span-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-4">
          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Estado página</p>
            <p className="text-sm font-bold">{activePage?.title || "Sin página"}</p>
            <p className="text-[10px] uppercase tracking-widest text-slate-400">{activePage?.status || "-"}</p>
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
            <div className="rounded-xl border border-slate-200 dark:border-white/10 p-3 space-y-2">
              <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">SEO</p>
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
                <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5">
                  <img src={seoImageDraft} alt="Imagen SEO" className="h-24 w-full object-cover" />
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-300 dark:border-white/20 bg-slate-50 dark:bg-white/5 p-3 text-center text-[10px] font-bold uppercase tracking-widest text-slate-400">
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
                className="w-full rounded-lg bg-blue-600 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-white inline-flex items-center justify-center gap-2 disabled:opacity-50"
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
              className="w-full rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
            >
              Guardar pagina/SEO
            </button>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} disabled={!canEdit && !canPublish} placeholder="Nota para workflow..." className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs disabled:opacity-60" />
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => runWorkflow("submit_review")} disabled={!activeSlug || !canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"><Send size={11} /> Review</button>
              <button onClick={() => runWorkflow("approve")} disabled={!activeSlug || !canPublish} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"><Save size={11} /> Aprobar</button>
              <button onClick={() => runWorkflow("publish")} disabled={!activeSlug || !canPublish} className="rounded-lg bg-primary text-white px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"><Upload size={11} /> Publicar</button>
              <button onClick={() => runWorkflow("revert_draft")} disabled={!activeSlug || !canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"><Undo2 size={11} /> Draft</button>
              <button onClick={() => runWorkflow("archive")} disabled={!activeSlug || !canPublish} className="col-span-2 rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50">Archivar</button>
            </div>
            <button
              onClick={() => {
                if (!activeSlug) return;
                window.open(`/cms/preview?site=${encodeURIComponent(siteKey)}&page=${encodeURIComponent(activeSlug)}`, "_blank");
              }}
              disabled={!activeSlug}
              className="w-full rounded-lg border border-blue-200 text-blue-600 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"
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
              className="w-full rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"
            >
              <ExternalLink size={11} /> Ver página pública
            </button>
              <button
                onClick={togglePageArchive}
                disabled={!activePage || !canEdit}
                className={`w-full rounded-lg border px-2 py-1.5 text-[10px] font-black uppercase tracking-widest disabled:opacity-50 ${activePage?.status === "archived" ? "border-emerald-200 text-emerald-600" : "border-amber-200 text-amber-600"}`}
              >
                {activePage?.status === "archived" ? "Restaurar pagina" : "Archivar pagina"}
              </button>
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Inspector sección</p>
            {!activeSection ? (
              <p className="text-xs text-slate-500">Selecciona una sección del canvas.</p>
            ) : (
              <fieldset disabled={!canEdit} className="space-y-0 disabled:opacity-60">
                <p className="text-xs font-bold uppercase tracking-widest text-slate-500">{activeSection.type}</p>
                <input
                  value={safeString(activeSection.props_json?.title)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("title", e.target.value)}
                  placeholder="Título"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
                <textarea
                  value={safeString(activeSection.props_json?.body)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), body: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("body", e.target.value)}
                  placeholder="Contenido"
                  className="w-full min-h-[90px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
                <input
                  value={safeString(activeSection.props_json?.cta_label)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), cta_label: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("cta_label", e.target.value)}
                  placeholder="Texto CTA"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
                <input
                  value={safeString(activeSection.props_json?.cta_href)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), cta_href: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("cta_href", e.target.value)}
                  placeholder="URL CTA"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />

                {(activeSection.type === "hero" || activeSection.type === "gallery") && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                      {activeSection.type === "hero" ? "Imagen hero" : "Imagen de galeria"}
                    </p>
                    {safeString(activeSection.props_json?.image_url) ? (
                      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5">
                        <img src={safeString(activeSection.props_json?.image_url)} alt={safeString(activeSection.props_json?.image_alt) || "Imagen seleccionada"} className="h-28 w-full object-cover" />
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-slate-300 dark:border-white/20 bg-slate-50 dark:bg-white/5 p-4 text-center text-[10px] font-bold uppercase tracking-widest text-slate-400">
                        Sin imagen seleccionada
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        setMediaPickerTarget("section");
                        setMediaPickerOpen(true);
                      }}
                      className="w-full rounded-lg bg-blue-600 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-white inline-flex items-center justify-center gap-2"
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
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                    />
                    <input
                      value={safeString(activeSection.props_json?.image_alt)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), image_alt: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("image_alt", e.target.value)}
                      placeholder="Texto alternativo"
                      className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
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
                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                  />
                )}

                {activeSection.type === "cards" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Items de tarjetas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                      <div key={`card-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                        {isItemArchived && <p className="text-[9px] font-black uppercase tracking-widest text-amber-700">Archivado</p>}
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
                        <button
                          onClick={() => {
                            const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-black uppercase tracking-widest ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}
                        >
                          {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                          {isItemArchived ? "Restaurar item" : "Archivar item"}
                        </button>
                      </div>
                      );
                    })}
                    <button
                      onClick={() => {
                        const nextProps = addArrayItem("items", { title: "Nueva tarjeta", body: "Descripción", status: "published" });
                        if (nextProps) saveSectionProps(nextProps);
                      }}
                      className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-black uppercase tracking-widest"
                    >
                      + Añadir tarjeta
                    </button>
                  </div>
                )}

                {activeSection.type === "faq" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Preguntas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                      <div key={`faq-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-200/70 dark:border-white/10"}`}>
                        {isItemArchived && <p className="text-[9px] font-black uppercase tracking-widest text-amber-700">Archivado</p>}
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
                          className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-black uppercase tracking-widest ${isItemArchived ? "border-emerald-200 text-emerald-700" : "border-amber-200 text-amber-700"}`}
                        >
                          {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                          {isItemArchived ? "Restaurar pregunta" : "Archivar pregunta"}
                        </button>
                      </div>
                      );
                    })}
                    <button
                      onClick={() => {
                        const nextProps = addArrayItem("items", { q: "Nueva pregunta", a: "Respuesta", status: "published" });
                        if (nextProps) saveSectionProps(nextProps);
                      }}
                      className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-black uppercase tracking-widest"
                    >
                      + Añadir pregunta
                    </button>
                  </div>
                )}

                <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">JSON avanzado</p>
                  <textarea
                    value={rawPropsDraft}
                    onChange={(e) => {
                      setRawPropsDraft(e.target.value);
                      setRawPropsError(null);
                    }}
                    className="w-full min-h-[120px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs font-mono"
                  />
                  <button
                    onClick={() => {
                      try {
                        const parsed = JSON.parse(rawPropsDraft);
                        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
                          setRawPropsError("El JSON debe ser un objeto.");
                          return;
                        }
                        setRawPropsError(null);
                        saveSectionProps(parsed as Record<string, unknown>);
                      } catch {
                        setRawPropsError("JSON inválido.");
                      }
                    }}
                    className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-black uppercase tracking-widest"
                  >
                    Guardar JSON
                  </button>
                  {rawPropsError && <p className="text-[10px] text-rose-500">{rawPropsError}</p>}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => setSectionVisibility(!activeSection.is_visible)} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1">
                    {activeSection.is_visible ? <EyeOff size={11} /> : <Eye size={11} />} {activeSection.is_visible ? "Ocultar" : "Mostrar"}
                  </button>
                  <button onClick={duplicateSection} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1">
                    <Copy size={11} /> Duplicar
                  </button>
                  <button onClick={toggleSectionArchive} className={`col-span-2 rounded-lg border px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 ${activeSection.status === "archived" ? "border-emerald-200 text-emerald-600" : "border-amber-200 text-amber-600"}`}>
                    {activeSection.status === "archived" ? <RotateCcw size={11} /> : <Archive size={11} />}
                    {activeSection.status === "archived" ? "Restaurar seccion" : "Archivar seccion"}
                  </button>
                </div>
                <p className="text-[10px] text-slate-400">{saving ? "Guardando..." : "Cambios guardados al salir del campo"}</p>
              </fieldset>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Versiones</p>
            <div className="max-h-44 overflow-auto space-y-2 pr-1">
              {versions.map((version) => (
                <button key={version.id} onClick={() => rollback(version.id)} disabled={!canPublish} className="w-full rounded-lg border border-slate-200 dark:border-white/10 p-2 text-left text-xs hover:border-primary/40 transition-all disabled:opacity-50">
                  <p className="font-black">v{version.version_number}</p>
                  <p className="text-[10px] text-slate-400">{new Date(version.created_at).toLocaleString()}</p>
                </button>
              ))}
              {versions.length === 0 && <p className="text-xs text-slate-500">Aún sin versiones publicadas.</p>}
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Historial</p>
            <div className="max-h-44 overflow-auto space-y-2 pr-1">
              {publishLogs.map((entry) => {
                const notes = typeof entry.metadata_json?.notes === "string" ? entry.metadata_json.notes : "";
                return (
                  <div key={entry.id} className="rounded-lg border border-slate-200 dark:border-white/10 p-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-black uppercase tracking-widest text-[10px]">{entry.action}</p>
                      <p className="text-[10px] text-slate-400">{new Date(entry.created_at).toLocaleString()}</p>
                    </div>
                    <p className="mt-1 text-[10px] text-slate-500">{entry.from_status || "sin estado"} &rarr; {entry.to_status || "sin estado"}</p>
                    {notes && <p className="mt-1 text-[10px] text-slate-400 line-clamp-2">{notes}</p>}
                  </div>
                );
              })}
              {publishLogs.length === 0 && <p className="text-xs text-slate-500">Aun sin eventos de workflow.</p>}
            </div>
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

