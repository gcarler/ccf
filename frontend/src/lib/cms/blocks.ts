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
      secondary_cta: "Ver predicaciones",
      bg_image: "https://images.unsplash.com/photo-1504051771394-dd2e66b2e08f?auto=format&fit=crop&w=1800&q=80"
    }
  },
  {
    key: `${SITE_KEY}_home_feed`,
    label: "Inicio — Contenido",
    description: "Tarjetas editoriales e imágenes de entrada del home.",
    page: "/",
    sample: {
      eyebrow: "Nuestra esencia",
      section_title: "Bienvenidos a Casa",
      section_description: "Rutas públicas para conocer la comunidad, profundizar en la fe y encontrar dónde dar el siguiente paso.",
      featured_card: {
        title: "Conocer a Jesús",
        desc: "Descubre la base de nuestra fe a través de un viaje personal y transformador.",
        href: "/conocer-a-jesus",
        cta: "Empezar el camino",
        img: "https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?w=900&q=80",
        alt: "Reunión de personas en comunidad"
      },
      cards: [
        {
          title: "Librería",
          desc: "Recursos para profundizar en tu estudio bíblico.",
          href: "/cursos",
          img: "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&q=80",
          alt: "Libros y estudio"
        }
      ]
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
    key: `${SITE_KEY}_events_feed`,
    label: "Eventos — Contenido",
    description: "Filtros, estados vacíos y etiquetas de eventos públicos.",
    page: "/eventos",
    sample: {
      empty_title: "Esperando agenda desde el CMS",
      empty_description: "Cuando haya eventos reales publicados, apareceran aqui sin contenido simulado.",
      no_events_title: "Sin eventos publicados",
      no_events_description: "Cuando el CMS publique eventos, apareceran aqui sin tarjetas inventadas.",
      calendar_title: "Explora nuestro Calendario",
      calendar_description: "Organiza tu tiempo con nuestras actividades comunitarias.",
      today_label: "HOY",
      upcoming_label: "Proximo en 48 horas",
      featured_badge: "Destacado",
      reserve_cta: "Reservar lugar",
      filters: ["Todos", "Conferencias", "Grupos de Conexión", "Cursos & Talleres", "Especiales"],
      featured_empty_title: "Evento destacado",
      featured_empty_description: "Contenido real desde el CMS",
      channel_link_label: "Ver canal"
    }
  },
  {
    key: `${SITE_KEY}_testimonials_hero`,
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
    key: `${SITE_KEY}_testimonials_feed`,
    label: "Testimonios — Contenido",
    description: "Búsqueda, estados vacíos y llamada a publicar testimonios.",
    page: "/testimonios",
    sample: {
      search_placeholder: "Buscar por tema, nombre o palabra clave",
      loading_label: "Cargando...",
      empty_title: "Todavía no hay testimonios publicados",
      empty_description: "Cuando el CMS publique testimonios, aparecerán aquí.",
      cta_label: "Compartir mi historia"
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
    key: `${SITE_KEY}_sermons_feed`,
    label: "Prédicas — Contenido",
    description: "Etiquetas y estados del catálogo de prédicas.",
    page: "/predicas",
    sample: {
      hero_eyebrow: "Ministerios Faro Oficial",
      hero_title_lead: "Prédicas &",
      hero_title_accent: "Mensajes",
      hero_description: "Alimento para el alma — explora los mensajes más recientes de nuestro canal de YouTube.",
      featured_label: "Último mensaje",
      grid_label: "Más mensajes",
      results_label: "Resultados",
      empty_title: "No se pudieron cargar los videos",
      empty_description: "Verifica tu conexión o intenta nuevamente.",
      search_placeholder: "Buscar por título o predicador…",
      clear_search_label: "Limpiar búsqueda",
      watched_label: "Visto",
      more_videos_label: "videos",
      channel_link_label: "Ver canal",
      cta_label: "Ver todos en YouTube",
      no_results_prefix: "Sin resultados para",
      no_results_description: "Intenta con otro término."
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
      hero_image_url: "https://picsum.photos/seed/1481627834876-b7833e8f5570/1920/1080",
      featured_fallback_image_url: "https://picsum.photos/seed/1524178232363-1fb2b075b655/800/600",
      cta_images: [
        { src: "https://picsum.photos/seed/academia1/800/800", alt: "Estudio" },
        { src: "https://picsum.photos/seed/academia2/800/800", alt: "Librería" }
      ],
      library_title: "Nuestra Librería",
      library_description: "Una curaduría de obras que han transformado generaciones.",
      empty_books_message: "Próximamente tendremos libros disponibles.",
      courses_title: "Cursos & Academia",
      courses_description: "Programas estructurados para líderes, estudiantes y buscadores de la verdad.",
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
      cta: "Quiero conocer a Jesús",
      bg_image: "https://picsum.photos/seed/1518623489648-a173ef7824f3/800/600"
    }
  },
  {
    key: `${SITE_KEY}_discover_feed`,
    label: "Conocer a Jesús — Contenido",
    description: "Pasos, contacto y recursos para nuevos creyentes.",
    page: "/conocer-a-jesus",
    sample: {
      intro_title: "Un Encuentro Personal",
      intro_paragraph_1: "En FARO, creemos que cada historia es única. No importa dónde hayas estado o qué hayas hecho, la invitación es la misma: Ven y ve.",
      intro_paragraph_2: "Descubre un espacio donde las preguntas son bienvenidas y la gracia es el lenguaje principal.",
      testimonials_title: "Historias que iluminan",
      testimonials_empty_title: "Próximamente compartiremos historias de transformación.",
      contact_title: "Hablemos de Tu Caminar",
      contact_description: "¿Tienes dudas? ¿Quieres orar por algo específico? Nuestro equipo está aquí para acompañarte sin juicios.",
      contact_email: "",
      contact_phone: "",
      contact_address: "",
      name_label: "Nombre completo",
      name_placeholder: "Tu nombre",
      phone_label: "WhatsApp",
      phone_placeholder: "+57 300...",
      message_label: "¿En qué podemos ayudarte?",
      message_placeholder: "Cuéntanos un poco sobre ti o tu petición de oración...",
      submit_label: "Enviar mensaje y conectar",
      benefits: [
        { icon: "Heart", title: "Gracia sin condenas", desc: "Eres bienvenido tal como eres." },
        { icon: "Star", title: "Propósito real", desc: "Descubre para qué fuiste creado." }
      ],
      contact_info: [
        { icon: "Clock", text: "Respuesta en menos de 24 horas" }
      ]
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
    key: `${SITE_KEY}_pastores_index`,
    label: "Liderazgo — Contenido",
    description: "Hero y estados vacíos de la página de pastores.",
    page: "/pastores",
    sample: {
      hero_badge: "Conoce a nuestro equipo pastoral",
      hero_title: "Liderazgo Pastoral",
      hero_description: "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.",
      loading_label: "Cargando...",
      empty_title: "No hay líderes pastorales registrados aún.",
      card_cta: "Conocer más",
      principal_label: "Pastor Principal"
    }
  },
  {
    key: `${SITE_KEY}_boletin_hero`,
    label: "Boletín — Hero",
    description: "Portada del boletín informativo.",
    page: "/boletin",
    sample: {
      subtitle: "Boletín Semanal FARO",
      title: "Recibe nuestra palabra de aliento",
      description: "Cada semana te enviamos una reflexión bíblica, un versículo de ánimo y consejos prácticos para fortalecer tu fe.",
      cta_text: "Suscribirme ahora"
    }
  },
  {
    key: `${SITE_KEY}_footer`,
    label: "Footer — Público",
    description: "Descripción, enlaces y redes del pie de página público.",
    page: "*",
    sample: {
      description: "Iluminando el camino hacia una conexión profunda con lo divino a través de la comunidad y la guía espiritual.",
      nav_links: [
        { href: "/", label: "Inicio" },
        { href: "/nosotros", label: "Sobre Nosotros" }
      ],
      resource_links: [
        { href: "/conocer-a-jesus", label: "Conocer a Jesús" },
        { href: "/testimonios", label: "Testimonios" }
      ],
      social_links: [
        { href: "https://facebook.com/comunidadfaro", label: "Facebook", kind: "facebook" }
      ],
      location_label: "Cartagena, Colombia",
      newsletter_label: "Boletín semanal"
    }
  },
  {
    key: `${SITE_KEY}_mobile_nav`,
    label: "Navegación Móvil — Público",
    description: "Botones visibles del menú móvil público.",
    page: "*",
    sample: {
      items: [
        { href: "/", label: "Inicio", icon: "home" },
        { href: "/eventos", label: "Eventos", icon: "calendar" },
        { href: "/predicas", label: "Prédicas", icon: "play" }
      ]
    }
  },
  {
    key: `${SITE_KEY}_welcome`,
    label: "Bienvenida — Pantalla",
    description: "Título, CTA y tarjetas de acceso para la ruta de bienvenida.",
    page: "/bienvenida",
    sample: {
      eyebrow: "Bienvenida",
      title_template: "Hola, {name}.",
      description: "No encontramos una cuenta registrada todavía, pero no te dejamos en una pantalla vacía.",
      primary_cta: { href: "/cursos", label: "Discipulado Básico" },
      secondary_cta: { href: "/conocer-a-jesus", label: "Una nueva vida con Cristo" },
      highlights: [
        {
          title: "Discipulado Básico",
          description: "Empieza por la ruta de fundamentos para crecer con orden y acompañamiento.",
          href: "/cursos",
          cta: "Ver academia",
          icon: "book"
        }
      ]
    }
  },
  {
    key: `${SITE_KEY}_privacy`,
    label: "Privacidad — Política",
    description: "Cabecera y secciones de la política de privacidad pública.",
    page: "/privacidad",
    sample: {
      last_update: "12 de junio de 2026",
      summary: "Esta política describe cómo PLES SAS y la Comunidad Cristiana El Faro recopilan, usan, almacenan y protegen tus datos personales.",
      sections: [
        { id: "responsables", title: "1. Responsables del tratamiento" },
        { id: "datos-recopilados", title: "2. Datos que recopilamos" }
      ]
    }
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

export const SITE_EVENTS_BLOCK_KEY = `${SITE_KEY}_public_events`;
export const SITE_MEDIA_BLOCK_KEY  = `${SITE_KEY}_media_gallery`;

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
