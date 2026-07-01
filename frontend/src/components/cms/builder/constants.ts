// ── Section type registry ───────────────────────────────────────────────────

export const SECTION_TYPES = [
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
] as const;

export type SectionType = (typeof SECTION_TYPES)[number];

export const SECTION_TYPE_COLORS: Record<string, string> = {
  hero:              "bg-[hsl(var(--primary))]",
  video_hero:        "bg-[hsl(var(--primary))]",
  rich_text:         "bg-[hsl(var(--surface-2))]",
  rich_text_columns: "bg-[hsl(var(--surface-2))]",
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
  collapsible:       "bg-[hsl(var(--primary))]",
  social_links:      "bg-sky-500",
  spacer:            "bg-stone-400",
  calendar:          "bg-[hsl(var(--primary))]",
  map:               "bg-[hsl(var(--secondary))]",
  document_upload:   "bg-amber-600",
  content_blocks:    "bg-pink-400",
  accordion:              "bg-teal-500",
  civic_hero_search:      "bg-[hsl(var(--primary))]",
  civic_convocatoria_cards: "bg-emerald-700",
  civic_quick_links:      "bg-sky-600",
  civic_file_downloads:   "bg-rose-600",
  civic_data_table:       "bg-teal-700",
  civic_alert_banner:     "bg-[hsl(var(--destructive))]",
};

export const SECTION_TYPE_LABEL: Record<string, string> = {
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

// ── Page templates ──────────────────────────────────────────────────────────

export interface PageTemplateSection {
  type: string;
  props_json: Record<string, unknown>;
}

export interface PageTemplate {
  key: string;
  label: string;
  sections: PageTemplateSection[];
}

export const PAGE_TEMPLATES: PageTemplate[] = [
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
            { q: "Cómo empezar?", a: "Visítanos y te acompañamos en tu proceso." },
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

// ── Section templates ───────────────────────────────────────────────────────

export interface SectionTemplate {
  label: string;
  type: string;
  props_json: Record<string, unknown>;
}

export const SECTION_TEMPLATES: SectionTemplate[] = [
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
