export interface CmsBlockDefinition {
  key: string;
  label: string;
  description: string;
  page: string;
  sample: Record<string, unknown> | unknown[];
}

export const FARO_BLOCKS: CmsBlockDefinition[] = [
  {
    key: "faro_nav_items",
    label: "Navegacion FARO",
    description: "Enlaces del navbar publico de FARO.",
    page: "/",
    sample: {
      items: [
        { label: "Sobre Nosotros", href: "/nosotros" },
        { label: "Testimonios", href: "/testimonios" },
        { label: "Eventos", href: "/eventos" },
        { label: "Predicas", href: "/predicas" },
        { label: "Cursos", href: "/cursos" },
        { label: "Sedes", href: "/sedes" }
      ]
    }
  },
  {
    key: "faro_home_hero",
    label: "Inicio hero",
    description: "Copys y CTAs del hero principal.",
    page: "/",
    sample: {
      eyebrow: "Comunidad FARO",
      title_lead: "Ilumina tu",
      title_accent: "Camino",
      description: "Una comunidad vibrante donde la fe encuentra proposito.",
      primary_cta: "Unete a nosotros",
      secondary_cta: "Ver predicaciones"
    }
  },
  {
    key: "faro_events_hero",
    label: "Eventos hero",
    description: "Titular y texto principal de eventos.",
    page: "/eventos",
    sample: {
      eyebrow: "Calendario de Comunidad",
      title: "Nuestra Agenda",
      description: "Espacios disenados para el crecimiento y la conexion."
    }
  },
  {
    key: "faro_testimonios_hero",
    label: "Testimonios hero",
    description: "Titular y subtitulo de testimonios.",
    page: "/testimonios",
    sample: {
      eyebrow: "Impacto Real",
      title_lead: "Historias de",
      title_accent: "Transformacion",
      description: "Descubre como la fe ha iluminado vidas reales."
    }
  },
  {
    key: "faro_sermons_hero",
    label: "Predicas hero",
    description: "Mensaje principal de la pagina de predicas.",
    page: "/predicas",
    sample: {
      eyebrow: "Mensaje Destacado",
      title_lead: "Alimento para el",
      title_accent: "Alma",
      description: "Biblioteca de mensajes para nutrir la fe."
    }
  },
  {
    key: "faro_courses_hero",
    label: "Cursos hero",
    description: "Texto de portada para cursos y libreria.",
    page: "/cursos",
    sample: {
      eyebrow: "Formacion y Sabiduria",
      title_lead: "El Camino",
      title_accent: "del Faro",
      description: "Explora cursos y recursos para profundizar tu fe."
    }
  },
  {
    key: "faro_discover_hero",
    label: "Conocer a Jesus hero",
    description: "Copys del encabezado principal.",
    page: "/conocer-a-jesus",
    sample: {
      eyebrow: "Inicia Tu Camino",
      title_lead: "La Luz que",
      title_accent: "Guia",
      title_tail: "Tu Vida.",
      description: "El comienzo de una relacion que transforma tu historia.",
      cta: "Quiero conocer a Jesus"
    }
  },
  {
    key: "faro_about_hero",
    label: "Nosotros hero",
    description: "Mensaje principal de identidad institucional.",
    page: "/nosotros",
    sample: {
      eyebrow: "Nuestra Identidad",
      title_lead: "Iluminando el",
      title_accent: "camino juntos",
      description: "Comunidad dedicada a guiar personas hacia una vida con proposito."
    }
  },
  {
    key: "faro_locations_hero",
    label: "Sedes hero",
    description: "Titulo y buscador para sedes y horarios.",
    page: "/sedes",
    sample: {
      eyebrow: "Nuestra Presencia",
      title: "Nuestras Sedes",
      search_placeholder: "Buscar ciudad o direccion..."
    }
  },
  {
    key: "faro_testimonials_feed",
    label: "Testimonios feed",
    description: "Listado moderado de testimonios publicos.",
    page: "/testimonios",
    sample: [
      {
        id: 1,
        content: "Llegue con ansiedad y hoy tengo paz y comunidad.",
        emotion: "Restauracion",
        is_approved: true,
        show_on_home: true,
        author_id: 1,
        author: { id: 1, username: "Comunidad FARO" },
        created_at: "2026-01-10T10:00:00Z"
      }
    ]
  },
  {
    key: "faro_announcements_feed",
    label: "Anuncios feed",
    description: "Publicaciones breves de comunicacion oficial.",
    page: "/plataforma/community/announcements",
    sample: [
      {
        id: 1,
        title: "Congreso de Jovenes",
        content: "Inscripciones abiertas en recepcion y web.",
        category: "Eventos",
        is_active: true,
        created_at: "2026-01-10T10:00:00Z"
      }
    ]
  }
];

export const FARO_MEDIA_BLOCK_KEY = "faro_media_gallery";
export const FARO_EVENTS_BLOCK_KEY = "faro_public_events";
