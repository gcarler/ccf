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
  // M1 R1
  "animated_counter", "video_embed", "gallery_masonry", "map_embed",
] as const;

export type SectionType = (typeof SECTION_TYPES)[number];

export const SECTION_TYPE_COLORS: Record<string, string> = {
  hero:              "bg-[hsl(var(--primary))]",
  video_hero:        "bg-[hsl(var(--primary))]",
  rich_text:         "bg-[hsl(var(--surface-2))]",
  rich_text_columns: "bg-[hsl(var(--surface-2))]",
  cards:             "bg-[hsl(var(--primary))]",
  cta_banner:        "bg-[hsl(var(--success))]",
  gallery:           "bg-[hsl(var(--domain-pink))]",
  faq:               "bg-[hsl(var(--warning))]",
  embed:             "bg-[hsl(var(--domain-cyan))]",
  testimonials:      "bg-[hsl(var(--danger))]",
  stats:             "bg-[hsl(var(--domain-teal))]",
  team:              "bg-orange-500",
  countdown:         "bg-[hsl(var(--destructive))]",
  pricing:           "bg-[hsl(var(--info))]",
  image_text:        "bg-[hsl(var(--primary))]",
  timeline:          "bg-[hsl(var(--domain-lime))]",
  icon_grid:         "bg-yellow-600",
  newsletter:        "bg-[hsl(var(--primary))]",
  popup_banner:      "bg-[hsl(var(--danger))]",
  button:            "bg-[hsl(var(--primary))]",
  toc:               "bg-[hsl(var(--text-secondary))]",
  divider:           "bg-[hsl(var(--border))]",
  collapsible:       "bg-[hsl(var(--primary))]",
  social_links:      "bg-[hsl(var(--info))]",
  spacer:            "bg-[hsl(var(--surface-3))]",
  calendar:          "bg-[hsl(var(--primary))]",
  map:               "bg-[hsl(var(--secondary))]",
  document_upload:   "bg-[hsl(var(--warning))]",
  content_blocks:    "bg-[hsl(var(--domain-pink))]",
  accordion:              "bg-[hsl(var(--domain-teal))]",
  civic_hero_search:      "bg-[hsl(var(--primary))]",
  civic_convocatoria_cards: "bg-[hsl(var(--success))]",
  civic_quick_links:      "bg-[hsl(var(--info))]",
  civic_file_downloads:   "bg-[hsl(var(--danger))]",
  civic_data_table:       "bg-[hsl(var(--domain-teal))]",
  civic_alert_banner:     "bg-[hsl(var(--destructive))]",
  animated_counter:       "bg-[hsl(var(--domain-teal))]",
  video_embed:            "bg-[hsl(var(--primary))]",
  gallery_masonry:        "bg-[hsl(var(--domain-pink))]",
  map_embed:              "bg-[hsl(var(--secondary))]",
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
  animated_counter:       "Contador Animado",
  video_embed:            "Video Embed",
  gallery_masonry:        "Galería Masonry",
  map_embed:              "Mapa Embed",
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
      eyebrow: "Bienvenido a casa",
      title_lead: "Una comunidad",
      title_accent: "que transforma",
      title_tail: "vidas",
      description: "Conecta con Jesús, crece en discipulado y sirve con propósito.",
      primary_cta: "Planifica tu visita",
      primary_cta_href: "/conocer-a-jesus",
      secondary_cta: "Ver eventos",
      secondary_cta_href: "/eventos",
      bg_image: "/images/convenccion/IMG_6813.webp",
    },
  },
  {
    label: "Hero con video",
    type: "video_hero",
    props_json: {
      title: "Vive la experiencia completa",
      body: "Un primer impacto visual para páginas especiales, campañas y eventos.",
      cta_label: "Conocer más",
      cta_href: "/nosotros",
      video_url: "",
    },
  },
  {
    label: "Pop-up informativo",
    type: "popup_banner",
    props_json: {
      title: "Aviso importante",
      body: "Comparte una invitación, campaña o anuncio temporal sin editar el contenido principal de la página.",
      cta_label: "Ver detalles",
      cta_href: "/eventos",
      delay_ms: 1200,
      show_on_paths: ["/"],
      hide_on_paths: ["/login", "/plataforma"],
      dismiss_mode: "local",
      dismiss_days: 7,
      dismiss_key: "",
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
  {
    label: "Contador Animado",
    type: "animated_counter",
    props_json: {
      title: "Nuestros Logros",
      items: [
        { label: "Miembros", value: 1200, prefix: "", suffix: "+", duration_ms: 2000 },
        { label: "Sedes", value: 5, prefix: "", suffix: "", duration_ms: 1500 },
        { label: "Proyectos", value: 48, prefix: "", suffix: "", duration_ms: 1800 },
      ],
    },
  },
  {
    label: "Video Embed",
    type: "video_embed",
    props_json: {
      title: "Video Destacado",
      video_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      caption: "Video explicativo sobre nuestra misión.",
      autoplay: false,
    },
  },
  {
    label: "Galería Masonry",
    type: "gallery_masonry",
    props_json: {
      title: "Nuestra Galería",
      columns: 3,
      images: [
        { url: "/images/convenccion/IMG_6813.webp", alt: "Imagen 1", caption: "Evento de convención" },
      ],
    },
  },
  {
    label: "Mapa Embed",
    type: "map_embed",
    props_json: {
      title: "Ubicación",
      address: "Bogotá, Colombia",
      lat: 4.6097,
      lng: -74.0817,
      zoom: 14,
      height_px: 400,
    },
  },
];

export const DEFAULT_SECTION_PROPS: Record<string, Record<string, unknown>> = {
  animated_counter: {
    title: "Nuestros Logros",
    items: [
      { label: "Miembros", value: 1200, prefix: "", suffix: "+", duration_ms: 2000 },
      { label: "Sedes", value: 5, prefix: "", suffix: "", duration_ms: 1500 },
      { label: "Proyectos", value: 48, prefix: "", suffix: "", duration_ms: 1800 },
    ],
  },
  video_embed: {
    title: "Video Destacado",
    video_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    caption: "Video explicativo sobre nuestra misión.",
    autoplay: false,
  },
  gallery_masonry: {
    title: "Nuestra Galería",
    columns: 3,
    images: [
      { url: "/images/convenccion/IMG_6813.webp", alt: "Imagen 1", caption: "Evento de convención" },
    ],
  },
  map_embed: {
    title: "Ubicación",
    address: "Bogotá, Colombia",
    lat: 4.6097,
    lng: -74.0817,
    zoom: 14,
    height_px: 400,
  },
};
