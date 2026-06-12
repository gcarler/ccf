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
      items: [
        {
          title: "Beca de Excelencia Académica 2025",
          description: "Dirigida a estudiantes de nivel superior con promedio mínimo de 8.5.",
          status: "abierta",
          deadline: "31 de julio de 2025",
          category: "Educación",
          href: "/convocatorias/beca-excelencia-2025"
        },
        {
          title: "Fondo para Proyectos Comunitarios",
          description: "Apoya iniciativas de impacto social en comunidades vulnerables.",
          status: "proxima",
          deadline: "1 de septiembre de 2025",
          category: "Desarrollo Social",
          href: "/convocatorias/fondo-comunitario-2025"
        },
        {
          title: "Premio Municipal de Arte 2024",
          description: "Reconocimiento a creadores locales en artes plásticas y visuales.",
          status: "cerrada",
          deadline: "15 de marzo de 2024",
          category: "Cultura",
          href: "/convocatorias/premio-arte-2024"
        }
      ]
    }
  },
  {
    key: "civic_quick_links",
    label: "Enlaces Rápidos (Cívico)",
    description: "Cuadrícula de botones grandes con icono, etiqueta y enlace a trámites frecuentes.",
    page: "*",
    sample: {
      title: "Trámites Frecuentes",
      body: "Los servicios más solicitados por la ciudadanía.",
      columns: "4",
      items: [
        { icon: "🪪", label: "Credencial de Elector",   href: "/tramites/credencial",  description: "Trámite INE" },
        { icon: "📋", label: "Acta de Nacimiento",      href: "/tramites/acta-nac",    description: "Registro Civil" },
        { icon: "🏠", label: "Predial",                 href: "/tramites/predial",     description: "Pago en línea" },
        { icon: "🚗", label: "Verificación Vehicular",  href: "/tramites/verificacion",description: "Programa 2025" },
        { icon: "💊", label: "Citas Médicas",           href: "/servicios/citas",      description: "IMSS / ISSSTE" },
        { icon: "🎓", label: "Becas Educativas",        href: "/becas",                description: "Ciclo 2025-2026" },
        { icon: "🌱", label: "Licencias Ambientales",   href: "/tramites/ambiental",   description: "Impacto ambiental" },
        { icon: "📞", label: "Contacto Ciudadano",      href: "/contacto",             description: "Atención directa" }
      ]
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
      items: [
        {
          name: "Convocatoria Beca 2025.pdf",
          file_url: "/docs/convocatoria-beca-2025.pdf",
          format: "pdf",
          size_label: "2.4 MB",
          description: "Bases y condiciones generales"
        },
        {
          name: "Formato de Solicitud.docx",
          file_url: "/docs/formato-solicitud.docx",
          format: "docx",
          size_label: "180 KB",
          description: "Llenar a máquina o a mano con tinta azul"
        },
        {
          name: "Presupuesto Aprobado 2025.xlsx",
          file_url: "/docs/presupuesto-2025.xlsx",
          format: "xlsx",
          size_label: "540 KB",
          description: "Ejercicio fiscal enero–diciembre 2025"
        }
      ]
    }
  },
  {
    key: "civic_data_table",
    label: "Tabla de Datos Accesible",
    description: "Tabla HTML accesible con caption, encabezados scope=\"col\" y primera columna scope=\"row\".",
    page: "*",
    sample: {
      title: "Resultados del Padrón 2025",
      caption: "Distribución de beneficiarios por municipio — Padrón 2025",
      highlight_first_col: true,
      striped: true,
      footer_note: "Fuente: Dirección General de Desarrollo Social, junio 2025.",
      headers: ["Municipio", "Solicitudes", "Aprobadas", "Rechazadas", "Pendientes"],
      rows: [
        ["Centro",        "1,240", "980",  "180", "80"],
        ["Norte",         "870",   "640",  "150", "80"],
        ["Sur",           "620",   "510",  "60",  "50"],
        ["Oriente",       "490",   "380",  "70",  "40"],
        ["Poniente",      "330",   "290",  "25",  "15"],
        ["Total general", "3,550", "2,800","485", "265"]
      ]
    }
  },
  {
    key: "civic_alert_banner",
    label: "Banner de Alerta / Emergencia",
    description: "Franja de alerta dismissible con nivel (info/warning/danger), título, mensaje y CTA opcional.",
    page: "*",
    sample: {
      level: "warning",
      title: "Mantenimiento Programado",
      message: "El portal de trámites en línea estará fuera de servicio el sábado 28 de junio de 06:00 a 10:00 hrs.",
      cta_label: "Más información",
      cta_href: "/avisos/mantenimiento-junio-2025",
      dismissible: true
    }
  }
];
