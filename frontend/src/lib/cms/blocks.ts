import { SITE_KEY } from "@/lib/site-config";

export interface CmsBlockDefinition {
  key: string;
  label: string;
  description: string;
  page: string;
  sample: Record<string, unknown> | unknown[];
}

export const SITE_BLOCKS: CmsBlockDefinition[] = [
  {
    key: `${SITE_KEY}_nav_items`,
    label: "Navegación Pública",
    description: "Enlaces del navbar público del sitio.",
    page: "/",
    sample: {
      items: [
        { label: "Sobre Nosotros", href: "/nosotros" },
        { label: "Testimonios", href: "/testimonios" },
        { label: "Eventos", href: "/eventos" },
        { label: "Prédicas", href: "/predicas" },
        { label: "Cursos", href: "/cursos" },
        { label: "Sedes", href: "/sedes" }
      ]
    }
  },
  {
    key: `${SITE_KEY}_home_hero`,
    label: "Inicio — Hero",
    description: "Copys y CTAs del hero principal.",
    page: "/",
    sample: {
      eyebrow: "Bienvenidos",
      title_lead: "Ilumina tu",
      title_accent: "Camino",
      description: "Una comunidad vibrante donde la fe encuentra propósito.",
      primary_cta: "Únete a nosotros",
      secondary_cta: "Ver predicaciones"
    }
  },
  {
    key: `${SITE_KEY}_events_hero`,
    label: "Eventos — Hero",
    description: "Titular y texto principal de eventos.",
    page: "/eventos",
    sample: {
      eyebrow: "Calendario de Comunidad",
      title: "Nuestra Agenda",
      description: "Espacios diseñados para el crecimiento y la conexión."
    }
  },
  {
    key: `${SITE_KEY}_testimonios_hero`,
    label: "Testimonios — Hero",
    description: "Titular y subtítulo de testimonios.",
    page: "/testimonios",
    sample: {
      eyebrow: "Impacto Real",
      title_lead: "Historias de",
      title_accent: "Transformación",
      description: "Descubre cómo la fe ha iluminado vidas reales."
    }
  },
  {
    key: `${SITE_KEY}_sermons_hero`,
    label: "Prédicas — Hero",
    description: "Mensaje principal de la página de prédicas.",
    page: "/predicas",
    sample: {
      eyebrow: "Mensaje Destacado",
      title_lead: "Alimento para el",
      title_accent: "Alma",
      description: "Biblioteca de mensajes para nutrir la fe."
    }
  },
  {
    key: `${SITE_KEY}_courses_hero`,
    label: "Cursos — Hero",
    description: "Texto de portada para cursos y librería.",
    page: "/cursos",
    sample: {
      eyebrow: "Formación y Sabiduría",
      title_lead: "El Camino del",
      title_accent: "Aprendizaje",
      description: "Explora cursos y recursos para profundizar tu fe."
    }
  },
  {
    key: `${SITE_KEY}_courses_feed`,
    label: "Cursos — Contenido",
    description: "Listado y configuración de cursos públicos.",
    page: "/cursos",
    sample: {
      featured_course_id: null,
      show_free_only: false
    }
  },
  {
    key: `${SITE_KEY}_discover_hero`,
    label: "Conocer a Jesús — Hero",
    description: "Copys del encabezado principal.",
    page: "/conocer-a-jesus",
    sample: {
      eyebrow: "Inicia Tu Camino",
      title_lead: "La Luz que",
      title_accent: "Guía",
      title_tail: "Tu Vida.",
      description: "El comienzo de una relación que transforma tu historia.",
      cta: "Quiero conocer a Jesús"
    }
  },
  {
    key: `${SITE_KEY}_discover_feed`,
    label: "Conocer a Jesús — Contenido",
    description: "Pasos, contacto y recursos para nuevos creyentes.",
    page: "/conocer-a-jesus",
    sample: {
      contact_email: "",
      contact_phone: "",
      contact_address: ""
    }
  },
  {
    key: `${SITE_KEY}_about_hero`,
    label: "Nosotros — Hero",
    description: "Mensaje principal de identidad institucional.",
    page: "/nosotros",
    sample: {
      eyebrow: "Nuestra Identidad",
      title_lead: "Caminando",
      title_accent: "juntos",
      description: "Comunidad dedicada a guiar personas hacia una vida con propósito."
    }
  },
  {
    key: `${SITE_KEY}_about_feed`,
    label: "Nosotros — Contenido",
    description: "Historia, visión, misión, valores y fundadores.",
    page: "/nosotros",
    sample: {
      vision_text: "Ser una comunidad de fe que <strong>transforma vidas, familias y ciudades</strong>.",
      mision_text: "Guiar, equipar y movilizar a cada persona mediante la <strong>enseñanza bíblica profunda</strong>.",
      founder_bio: "",
      founder_bio2: "",
      quote_text: "",
      quote_author: "",
      quote_subtitle: "",
      stats: [
        { value: "0+", label: "Miembros" },
        { value: "0+", label: "Años" },
        { value: "0", label: "Sedes" }
      ],
      valores: []
    }
  },
  {
    key: `${SITE_KEY}_locations_hero`,
    label: "Sedes — Hero",
    description: "Título y buscador para sedes y horarios.",
    page: "/sedes",
    sample: {
      eyebrow: "Nuestra Presencia",
      title: "Nuestras Sedes",
      search_placeholder: "Buscar ciudad o dirección..."
    }
  },
  {
    key: `${SITE_KEY}_locations_feed`,
    label: "Sedes — Contenido",
    description: "Mapa y listado de sedes con horarios.",
    page: "/sedes",
    sample: { show_map: true }
  },
  {
    key: `${SITE_KEY}_pastores_hero`,
    label: "Liderazgo — Hero",
    description: "Titular de la página de pastores.",
    page: "/pastores",
    sample: {
      eyebrow: "Nuestro Equipo",
      title: "Liderazgo Pastoral",
      description: "Personas llamadas a servir y guiar a la comunidad."
    }
  },
  {
    key: `${SITE_KEY}_pastores_feed`,
    label: "Liderazgo — Contenido",
    description: "Datos adicionales de la página de pastores.",
    page: "/pastores",
    sample: {}
  },
  {
    key: `${SITE_KEY}_boletin_hero`,
    label: "Boletín — Hero",
    description: "Portada del boletín informativo.",
    page: "/boletin",
    sample: {
      title: "Boletín de la Comunidad",
      description: "Las noticias y anuncios más recientes."
    }
  },
  {
    key: `${SITE_KEY}_testimonials_feed`,
    label: "Testimonios — Feed",
    description: "Listado moderado de testimonios públicos.",
    page: "/testimonios",
    sample: [
      {
        id: 1,
        content: "Llegué con ansiedad y hoy tengo paz y comunidad.",
        emotion: "Restauración",
        is_approved: true,
        show_on_home: true,
        created_at: "2026-01-10T10:00:00Z"
      }
    ]
  },
  {
    key: `${SITE_KEY}_announcements_feed`,
    label: "Anuncios — Feed",
    description: "Publicaciones breves de comunicación oficial.",
    page: "/plataforma/community/announcements",
    sample: [
      {
        id: 1,
        title: "Congreso de Jóvenes",
        content: "Inscripciones abiertas en recepción y web.",
        category: "Eventos",
        is_active: true,
        created_at: "2026-01-10T10:00:00Z"
      }
    ]
  }
];

// Keep FARO_BLOCKS as alias for backwards compat during transition
export const FARO_BLOCKS = SITE_BLOCKS;

export const SITE_EVENTS_BLOCK_KEY = `${SITE_KEY}_public_events`;
export const SITE_MEDIA_BLOCK_KEY  = `${SITE_KEY}_media_gallery`;

// Legacy aliases — remove after DB migration
export const FARO_EVENTS_BLOCK_KEY = SITE_EVENTS_BLOCK_KEY;
export const FARO_MEDIA_BLOCK_KEY  = SITE_MEDIA_BLOCK_KEY;

export const CIVIC_BLOCKS: CmsBlockDefinition[] = [
  {
    key: "civic_hero_search",
    label: "Buscador Hero (Cívico)",
    description: "Hero con buscador integrado para trámites, convocatorias y contenidos.",
    page: "*",
    sample: {
      eyebrow: "Portal de Trámites",
      title: "¿Qué trámite buscas?",
      subtitle: "Encuentra servicios, convocatorias y documentos en un solo lugar.",
      placeholder: "Buscar trámites, convocatorias, noticias...",
      action_url: "/buscar",
      background_image: "",
      suggestions: ["Licencia de conducir", "Registro civil", "Becas 2025"]
    }
  },
  {
    key: "civic_convocatoria_cards",
    label: "Tarjetas Convocatoria",
    description: "Cuadrícula de convocatorias con badge de estado (Abierta/Cerrada/Próxima) y fecha de cierre.",
    page: "*",
    sample: {
      title: "Convocatorias Vigentes",
      body: "Consulta las convocatorias activas y sus fechas límite.",
      items: []
    }
  },
  {
    key: "civic_quick_links",
    label: "Enlaces Rápidos (Cívico)",
    description: "Cuadrícula de botones grandes con icono, etiqueta y enlace a trámites frecuentes.",
    page: "*",
    sample: {
      title: "Trámites Frecuentes",
      body: "Los servicios más solicitados.",
      columns: "4",
      items: []
    }
  },
  {
    key: "civic_file_downloads",
    label: "Descargas de Archivos",
    description: "Lista de documentos descargables con icono de formato, tamaño y botón de descarga.",
    page: "*",
    sample: {
      title: "Documentos Disponibles",
      body: "Descarga los formatos y documentos oficiales.",
      items: []
    }
  },
  {
    key: "civic_data_table",
    label: "Tabla de Datos Accesible",
    description: "Tabla HTML accesible con caption, encabezados scope=\"col\" y primera columna scope=\"row\".",
    page: "*",
    sample: {
      title: "Resultados",
      caption: "",
      highlight_first_col: true,
      striped: true,
      footer_note: "",
      headers: [],
      rows: []
    }
  },
  {
    key: "civic_alert_banner",
    label: "Banner de Alerta / Emergencia",
    description: "Franja de alerta dismissible con nivel (info/warning/danger), título, mensaje y CTA opcional.",
    page: "*",
    sample: {
      level: "warning",
      title: "Aviso Importante",
      message: "",
      cta_label: "Más información",
      cta_href: "/avisos",
      dismissible: true
    }
  }
];
