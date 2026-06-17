"use client";

import React, { useMemo, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";
import {
  ArrowDownUp,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  Copy,
  FileText,
  GalleryHorizontalEnd,
  Globe2,
  GraduationCap,
  HeartHandshake,
  Layers3,
  LucideIcon,
  MapPinned,
  MessageCircleHeart,
  MonitorSmartphone,
  MousePointerClick,
  PackageOpen,
  Palette,
  PanelBottom,
  Search,
  Share2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  UserRoundPlus,
} from "lucide-react";
import clsx from "clsx";

type FlowType = "publish" | "capture" | "sync" | "system";

interface CmsResource {
  id: string;
  title: string;
  category: string;
  description: string;
  flow: FlowType;
  sectionType?: string;
  publicSurface: string;
  platformSource: string;
  readiness: "available" | "partial" | "planned";
  icon: LucideIcon;
  fields: string[];
  safeguards: string[];
  example: Record<string, unknown>;
}

const FLOW_LABEL: Record<FlowType, string> = {
  publish: "CMS -> Web",
  capture: "Web -> Plataforma",
  sync: "Plataforma -> Web",
  system: "Sistema CMS",
};

const FLOW_CLASS: Record<FlowType, string> = {
  publish: "bg-blue-50 text-[hsl(var(--primary))] border-blue-200 dark:bg-blue-500/10 dark:border-blue-500/20",
  capture: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/20",
  sync: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/20",
  system: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-white/5 dark:text-slate-300 dark:border-white/10",
};

const READINESS_LABEL = {
  available: "Disponible",
  partial: "Parcial",
  planned: "Por construir",
};

const RESOURCES: CmsResource[] = [
  {
    id: "hero-slider",
    title: "Hero / Slider principal",
    category: "Body",
    description: "Portadas, llamados principales, imagen o video de apertura y CTA hacia rutas publicas.",
    flow: "publish",
    sectionType: "hero / video_hero",
    publicSurface: "Home, landing, paginas institucionales",
    platformSource: "CMS Builder",
    readiness: "available",
    icon: SlidersHorizontal,
    fields: ["title", "body", "image_url", "video_url", "cta_label", "cta_href"],
    safeguards: ["Mantener fallback actual hasta publicar version", "Alt text obligatorio para imagenes", "CTA interno con rutas existentes"],
    example: {
      type: "hero",
      props_json: {
        title: "Una casa para conocer a Jesus",
        body: "Conecta con una comunidad y da tu siguiente paso.",
        image_url: "/media/hero.jpg",
        cta_label: "Quiero conocer a Jesus",
        cta_href: "/conocer-a-jesus",
      },
    },
  },
  {
    id: "gallery",
    title: "Galeria de imagenes",
    category: "Media",
    description: "Colecciones visuales para eventos, sedes, testimonios o recorridos de pagina.",
    flow: "publish",
    sectionType: "gallery",
    publicSurface: "Body, secciones de eventos, sedes, nosotros",
    platformSource: "CMS Media",
    readiness: "available",
    icon: GalleryHorizontalEnd,
    fields: ["items[].url", "items[].alt", "items[].caption"],
    safeguards: ["No publicar imagenes archivadas", "Texto alternativo por imagen", "Usar imagenes optimizadas"],
    example: {
      type: "gallery",
      props_json: {
        title: "Vida en comunidad",
        items: [
          { url: "/media/servicio-1.jpg", alt: "Servicio dominical", caption: "Domingo en FARO" },
          { url: "/media/grupo-1.jpg", alt: "Grupo reunido", caption: "Casas de bendicion" },
        ],
      },
    },
  },
  {
    id: "map",
    title: "Mapa y como llegar",
    category: "Ubicacion",
    description: "Bloque de sede con direccion, mapa embebido y boton automatico hacia indicaciones.",
    flow: "publish",
    sectionType: "map",
    publicSurface: "Sedes, eventos, landing de servicio",
    platformSource: "CMS Builder / agenda de eventos",
    readiness: "available",
    icon: MapPinned,
    fields: ["title", "address", "embed_url", "directions_url"],
    safeguards: ["Usar embed_url permitido", "Boton externo en nueva pestaña", "Direccion legible sin depender del iframe"],
    example: {
      type: "map",
      props_json: {
        title: "Sede principal",
        address: "Mocoa, Putumayo",
        embed_url: "https://www.google.com/maps/embed?...",
        directions_url: "https://maps.google.com/?q=FARO",
      },
    },
  },
  {
    id: "social-links",
    title: "Redes sociales",
    category: "Header / Footer",
    description: "Enlaces oficiales a redes, WhatsApp, YouTube, Instagram y canales externos.",
    flow: "publish",
    sectionType: "social_links",
    publicSurface: "Footer, contacto, bloques de comunidad",
    platformSource: "CMS Builder / temas",
    readiness: "available",
    icon: Share2,
    fields: ["items[].label", "items[].href", "items[].icon"],
    safeguards: ["Validar enlaces externos", "No mezclar redes personales", "Mantener target seguro"],
    example: {
      type: "social_links",
      props_json: {
        title: "Siguenos",
        items: [
          { label: "Instagram", href: "https://instagram.com/...", icon: "instagram" },
          { label: "YouTube", href: "https://youtube.com/...", icon: "youtube" },
        ],
      },
    },
  },
  {
    id: "courses",
    title: "Cursos publicados",
    category: "Academia",
    description: "Contenido de Academia visible en la pagina publica de cursos cuando esta publicado.",
    flow: "sync",
    sectionType: "content_blocks",
    publicSurface: "/cursos",
    platformSource: "Modulo Academia / public courses",
    readiness: "partial",
    icon: GraduationCap,
    fields: ["course.title", "course.description", "course.image_url", "is_published"],
    safeguards: ["Solo cursos publicados", "Fallback publico intacto", "No exponer cursos internos"],
    example: {
      source: "academy",
      filter: { published_only: true },
      target: "/cursos",
    },
  },
  {
    id: "events",
    title: "Eventos y agenda",
    category: "Eventos",
    description: "Eventos administrados en plataforma que pueden mostrarse en la web con fecha, lugar y como llegar.",
    flow: "sync",
    sectionType: "calendar / cards / map",
    publicSurface: "/eventos, home, landing",
    platformSource: "Agenda / Evangelismo eventos",
    readiness: "partial",
    icon: CalendarDays,
    fields: ["title", "date", "location", "image_url", "directions_url", "published"],
    safeguards: ["Publicar solo eventos aprobados", "Ocultar eventos vencidos si aplica", "Mantener capacidad y datos privados fuera de web"],
    example: {
      source: "events",
      filter: { is_public: true, upcoming: true },
      sectionTypes: ["calendar", "cards", "map"],
    },
  },
  {
    id: "books-resources",
    title: "Biblioteca de recursos",
    category: "Recursos",
    description: "Libros, PDFs, guias descargables, videos y materiales para formacion publica.",
    flow: "publish",
    sectionType: "document_upload / civic_file_downloads",
    publicSurface: "Cursos, recursos, paginas de discipulado",
    platformSource: "CMS Media / Academia recursos",
    readiness: "available",
    icon: BookOpen,
    fields: ["items[].title", "items[].file_url", "items[].type", "items[].description"],
    safeguards: ["Permisos de uso del archivo", "Peso de descarga visible", "No publicar material interno sin aprobacion"],
    example: {
      type: "document_upload",
      props_json: {
        title: "Recursos de discipulado",
        items: [{ title: "Guia de inicio", file_url: "/media/guia.pdf", type: "PDF" }],
      },
    },
  },
  {
    id: "footer",
    title: "Footer global",
    category: "Footer",
    description: "Informacion institucional, enlaces, sedes, datos legales, redes y CTA persistente.",
    flow: "publish",
    sectionType: "global block",
    publicSurface: "Todas las paginas publicas",
    platformSource: "CMS bloques globales / temas",
    readiness: "partial",
    icon: PanelBottom,
    fields: ["logo", "description", "links", "socials", "contact", "legal"],
    safeguards: ["Versionar antes de activar global", "No romper rutas publicas existentes", "Preview antes de publicar"],
    example: {
      global_key: `${SITE_KEY}_footer`,
      props_json: {
        description: "Una iglesia para la ciudad.",
        links: [{ label: "Conocer a Jesus", href: "/conocer-a-jesus" }],
      },
    },
  },
  {
    id: "discover-jesus-form",
    title: "Formulario Conocer a Jesus",
    category: "Captura CRM",
    description: "Entrada publica de personas interesadas que debe crear/contactar un caso en CRM/consolidacion.",
    flow: "capture",
    sectionType: "form bridge",
    publicSurface: "/conocer-a-jesus",
    platformSource: "CRM / consolidacion",
    readiness: "available",
    icon: UserRoundPlus,
    fields: ["name", "phone", "email", "message", "source"],
    safeguards: ["Consentimiento y privacidad", "Source trazable", "Evitar duplicados por telefono/correo"],
    example: {
      public_endpoint: "/crm/consolidation/cases",
      source: "conocer-a-jesus",
      crm_target: "consolidation",
    },
  },
  {
    id: "prayer-form",
    title: "Motivos de oracion",
    category: "Captura CRM",
    description: "Peticiones publicas que llegan al muro CRM para seguimiento pastoral.",
    flow: "capture",
    sectionType: "form bridge",
    publicSurface: "Testimonios, oracion, landing",
    platformSource: "CRM / prayer requests",
    readiness: "available",
    icon: MessageCircleHeart,
    fields: ["requester_name", "request_text", "category", "source"],
    safeguards: ["No mostrar publicamente sin aprobacion", "Datos sensibles protegidos", "Estado inicial pendiente"],
    example: {
      public_endpoint: "/crm/prayer-requests/public",
      source: "prayer-web",
      crm_target: "prayers",
    },
  },
  {
    id: "theme-fonts",
    title: "Temas, fuentes y tokens",
    category: "Sistema visual",
    description: "Paleta, logo, CTA, fuentes y variables visuales por sitio sin editar codigo publico.",
    flow: "system",
    sectionType: "theme tokens",
    publicSurface: "Sitio completo",
    platformSource: "CMS Temas",
    readiness: "available",
    icon: Palette,
    fields: ["--site-primary", "--site-logo-url", "--site-header-cta-label", "font_family"],
    safeguards: ["Contraste minimo", "No romper dark/light", "Activacion solo por publicadores"],
    example: {
      tokens_json: {
        "--site-primary": "#2563eb",
        "--site-logo-name": "FARO",
        "--site-header-cta-href": "/conocer-a-jesus",
      },
    },
  },
];

const CATEGORIES = ["Todos", ...Array.from(new Set(RESOURCES.map((item) => item.category)))];

function prettyJson(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}

export default function CmsResourcesPage() {
  const [category, setCategory] = useState("Todos");
  const [query, setQuery] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filteredResources = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return RESOURCES.filter((item) => {
      const matchesCategory = category === "Todos" || item.category === category;
      const matchesQuery = !normalized || [
        item.title,
        item.description,
        item.category,
        item.sectionType,
        item.publicSurface,
        item.platformSource,
      ].some((value) => String(value || "").toLowerCase().includes(normalized));
      return matchesCategory && matchesQuery;
    });
  }, [category, query]);

  const flowCounts = useMemo(() => {
    return RESOURCES.reduce<Record<FlowType, number>>((acc, item) => {
      acc[item.flow] += 1;
      return acc;
    }, { publish: 0, capture: 0, sync: 0, system: 0 });
  }, []);

  const copyExample = async (item: CmsResource) => {
    await navigator.clipboard.writeText(prettyJson(item.example));
    setCopiedId(item.id);
    window.setTimeout(() => setCopiedId(null), 1600);
  };

  return (
    <div className="h-full overflow-y-auto bg-slate-50 dark:bg-[#111213]">
      <div className="mx-auto max-w-7xl space-y-4 p-4">
        <section className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-[#141517]">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-3 inline-flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] dark:border-blue-500/20 dark:bg-blue-500/10">
                <PackageOpen size={13} />
                Biblioteca CMS
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                Recursos para publicar, sincronizar y capturar informacion
              </h1>
              <p className="mt-2 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                Este catalogo documenta los recursos disponibles para construir paginas publicas sin tocar el contenido actual:
                bloques visuales, recursos multimedia, datos que vienen de la plataforma y formularios que entran al CRM.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 lg:w-[420px]">
              {([
                ["publish", MonitorSmartphone],
                ["sync", ArrowDownUp],
                ["capture", MousePointerClick],
                ["system", ShieldCheck],
              ] as Array<[FlowType, LucideIcon]>).map(([flow, Icon]) => (
                <div key={flow} className="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                  <Icon size={16} className="text-slate-400" />
                  <p className="mt-2 text-lg font-bold text-slate-900 dark:text-white">{flowCounts[flow]}</p>
                  <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{FLOW_LABEL[flow]}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(220px,280px)_1fr]">
          <aside className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-[#141517]">
            <div className="relative">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar recurso..."
                className="h-9 w-full rounded-md border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm outline-none transition-all focus:border-[hsl(var(--primary))] focus:ring-2 focus:ring-blue-500/10 dark:border-white/10 dark:bg-black/20 dark:text-white"
              />
            </div>

            <div className="mt-3 space-y-1">
              {CATEGORIES.map((item) => (
                <button
                  key={item}
                  onClick={() => setCategory(item)}
                  className={clsx(
                    "flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-xs font-bold transition-colors",
                    category === item
                      ? "bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10"
                      : "text-slate-500 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-white",
                  )}
                >
                  {item}
                  <span className="text-[10px] text-slate-400">
                    {item === "Todos" ? RESOURCES.length : RESOURCES.filter((resource) => resource.category === item).length}
                  </span>
                </button>
              ))}
            </div>

            <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-200">
              <div className="flex items-center gap-2 font-bold uppercase tracking-wide">
                <CheckCircle2 size={14} />
                Sin impacto publico
              </div>
              <p className="mt-2 leading-relaxed">
                Esta biblioteca no publica cambios por si misma. Sirve como guia para construir nuevas secciones con preview y flujo editorial.
              </p>
            </div>
          </aside>

          <div className="space-y-3">
            <section className="grid grid-cols-1 gap-3 xl:grid-cols-2">
              {filteredResources.map((item) => {
                const Icon = item.icon;
                return (
                  <article key={item.id} className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-[#141517]">
                    <div className="flex items-start gap-3">
                      <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-slate-100 text-[hsl(var(--primary))] dark:bg-white/5">
                        <Icon size={18} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h2 className="text-base font-bold text-slate-900 dark:text-white">{item.title}</h2>
                          <span className={clsx("rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide", FLOW_CLASS[item.flow])}>
                            {FLOW_LABEL[item.flow]}
                          </span>
                          <span className="rounded-full border border-slate-200 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-slate-400 dark:border-white/10">
                            {READINESS_LABEL[item.readiness]}
                          </span>
                        </div>
                        <p className="mt-2 text-sm leading-relaxed text-slate-500 dark:text-slate-400">{item.description}</p>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Superficie publica</p>
                        <p className="mt-1 text-sm font-semibold text-slate-700 dark:text-slate-200">{item.publicSurface}</p>
                      </div>
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Fuente / destino</p>
                        <p className="mt-1 text-sm font-semibold text-slate-700 dark:text-slate-200">{item.platformSource}</p>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div>
                        <p className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">
                          <FileText size={13} />
                          Campos esperados
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {item.fields.map((field) => (
                            <span key={field} className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600 dark:bg-white/5 dark:text-slate-300">
                              {field}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">
                          <ShieldCheck size={13} />
                          Guardrails
                        </p>
                        <ul className="space-y-1.5">
                          {item.safeguards.map((guardrail) => (
                            <li key={guardrail} className="flex gap-2 text-xs text-slate-500 dark:text-slate-400">
                              <CheckCircle2 size={12} className="mt-0.5 shrink-0 text-emerald-500" />
                              {guardrail}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="mt-4 rounded-md border border-slate-200 bg-slate-950 p-3 dark:border-white/10">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">
                          <Layers3 size={13} />
                          Ejemplo de configuracion
                        </p>
                        <button
                          onClick={() => copyExample(item)}
                          className="inline-flex items-center gap-1.5 rounded-md bg-white/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-white transition-colors hover:bg-white/15"
                        >
                          <Copy size={12} />
                          {copiedId === item.id ? "Copiado" : "Copiar"}
                        </button>
                      </div>
                      <pre className="max-h-44 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate-200">
                        {prettyJson(item.example)}
                      </pre>
                    </div>
                  </article>
                );
              })}
            </section>

            {filteredResources.length === 0 && (
              <div className="rounded-md border border-dashed border-slate-300 bg-[hsl(var(--bg-primary))] p-8 text-center dark:border-white/10 dark:bg-[#141517]">
                <PackageOpen size={34} className="mx-auto text-slate-300" />
                <p className="mt-3 text-sm font-bold text-slate-700 dark:text-slate-200">No hay recursos con ese filtro</p>
                <p className="mt-1 text-xs text-slate-400">Prueba otra categoria o termino de busqueda.</p>
              </div>
            )}
          </div>
        </section>

        <section className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {[
            {
              icon: Globe2,
              title: "Publicacion controlada",
              body: "El CMS debe crear borradores, revisar, aprobar y publicar sin cambiar el sitio hasta que una version este lista.",
            },
            {
              icon: HeartHandshake,
              title: "Captura pastoral",
              body: "Los formularios publicos no son contenido: son entradas ministeriales que deben llegar al CRM con fuente y consentimiento.",
            },
            {
              icon: Sparkles,
              title: "Plataforma como fuente",
              body: "Cursos, eventos y testimonios aprobados nacen en sus modulos y el CMS decide si aparecen en la web.",
            },
          ].map((item) => (
            <div key={item.title} className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-[#141517]">
              <item.icon size={18} className="text-[hsl(var(--primary))]" />
              <h3 className="mt-3 text-sm font-bold text-slate-900 dark:text-white">{item.title}</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">{item.body}</p>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
