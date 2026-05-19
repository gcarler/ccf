import {
  Activity,
  BookOpen,
  Bot,
  Calendar,
  CheckSquare,
  Contact,
  FileText,
  GraduationCap,
  Heart,
  Home,
  Inbox,
  KanbanSquare,
  Layout,
  LayoutDashboard,
  Link2,
  Mail,
  MessageCircle,
  PieChart,
  Scan,
  Settings,
  ShieldCheck,
  UserPlus,
  Users,
  Zap,
  Plus,
  Shield,
} from 'lucide-react';

export const MODULE_CONFIGS: Record<string, any> = {
  projects: {
    title: 'Portfolio',
    sections: [
      {
        title: 'Gestión',
        items: [
          {
            id: 'projects-home',
            label: 'Portfolio',
            href: '/projects',
            icon: Layout,
          },
          {
            id: 'projects-tasks',
            label: 'Mis Tareas',
            href: '/tasks',
            icon: CheckSquare,
          },
          {
            id: 'projects-team',
            label: 'Equipo',
            href: '/projects/team',
            icon: Users,
          },
        ],
      },
      {
        title: 'Herramientas',
        items: [
          {
            id: 'projects-calendar',
            label: 'Calendario',
            href: '/calendar',
            icon: Calendar,
          },
          {
            id: 'projects-auto',
            label: 'Automatizaciones',
            href: '/projects/automations',
            icon: Zap,
          },
        ],
      },
    ],
  },
  tasks: {
    title: 'Productividad',
    sections: [
      {
        title: 'Mis espacios',
        items: [
          {
            id: 'tasks-all',
            label: 'Todas las tareas',
            href: '/tasks',
            icon: CheckSquare,
          },
          {
            id: 'tasks-calendar',
            label: 'Calendario',
            href: '/calendar',
            icon: Calendar,
          },
        ],
      },
    ],
  },
  "mi-vista": {
    title: "Mi Vista",
    sections: [
      {
        title: "Resumen Personal",
        items: [
          {
            id: "my-view-home",
            label: "Vista General",
            href: "/mi-vista",
            icon: LayoutDashboard,
          },
          {
            id: "my-view-tasks",
            label: "Mis Tareas",
            href: "/tasks",
            icon: CheckSquare,
          },
          {
            id: "my-view-inbox",
            label: "Mensajes",
            href: "/inbox",
            icon: Inbox,
          },
          {
            id: "my-view-calendar",
            label: "Calendario",
            href: "/calendar",
            icon: Calendar,
          },
        ],
      },
      {
        title: "Mi Cuenta",
        items: [
          {
            id: "my-view-profile",
            label: "Mi Perfil",
            href: "/account",
            icon: Users,
          },
          {
            id: "my-view-settings",
            label: "Configuración",
            href: "/settings",
            icon: Settings,
          },
        ],
      },
    ],
  },
  calendar: {
    title: 'Calendario',
    sections: [
      {
        title: 'Vistas',
        items: [
          {
            id: 'cal-month',
            label: 'Por Mes',
            href: '/calendar',
            icon: Calendar,
          },
        ],
      },
    ],
  },
  crm: {
    title: 'Comunidad CRM',
    sections: [
      {
        title: 'Actividad y Métricas',
        items: [
          {
            id: 'crm-analytics',
            label: 'Panel Analítico',
            href: '/crm/analytics',
            icon: PieChart,
          },
        ],
      },
      {
        title: 'Directorio Pastoral',
        items: [
          {
            id: 'crm-members',
            label: 'Miembros',
            href: '/crm/members',
            icon: Users,
          },
          {
            id: 'crm-groups',
            label: 'Faros en Casa',
            href: '/crm/groups',
            icon: Home,
          },
          {
            id: 'crm-contacts',
            label: 'Contactos/Leads',
            href: '/crm/contacts',
            icon: UserPlus,
          },
          {
            id: 'crm-volunteers',
            label: 'Voluntariado',
            href: '/crm/volunteers',
            icon: ShieldCheck,
          },
        ],
      },
      {
        title: 'Consolidación',
        items: [
          {
            id: 'crm-pipeline',
            label: 'Pipeline pastoral',
            href: '/crm/pipeline',
            icon: KanbanSquare,
          },
          {
            id: 'crm-counseling',
            label: 'Consejería',
            href: '/crm/counseling',
            icon: Heart,
          },
          {
            id: 'crm-prayers',
            label: 'Muro de Oración',
            href: '/crm/prayers',
            icon: MessageCircle,
          },
          {
            id: 'crm-tasks',
            label: 'Tareas Asignadas',
            href: '/crm/tasks',
            icon: CheckSquare,
          },
        ],
      },
      {
        title: 'Herramientas',
        items: [
          {
            id: 'crm-messaging',
            label: 'Mensajería',
            href: '/crm/messaging',
            icon: Mail,
          },
          {
            id: 'crm-mycard',
            label: 'Mi Carnet',
            href: '/crm/my-card',
            icon: Contact,
          },
          {
            id: 'crm-settings',
            label: 'Configuración',
            href: '/crm/settings',
            icon: Settings,
          },
        ],
      },
    ],
  },
  evangelism: {
    title: 'Evangelismo & Eventos',
    sections: [
      {
        title: 'Estrategia',
        items: [
          {
            id: 'ev-events',
            label: 'Eventos',
            href: '/evangelism/events',
            icon: Calendar,
          },
          {
            id: 'ev-faro',
            label: 'Faro: Panel',
            href: '/evangelism/faro',
            icon: Activity,
          },
          {
            id: 'ev-faro-groups',
            label: 'Grupos Faro',
            href: '/evangelism/faro/groups',
            icon: Home,
          },
          {
            id: 'ev-scanner',
            label: 'Escáner ASST',
            href: '/evangelism/scanner',
            icon: Scan,
          },
        ],
      },
      {
        title: 'Gestión Faro',
        items: [
          {
            id: 'faro-create',
            label: 'Crear Nuevo',
            href: '/evangelism/faro/groups?mode=create',
            icon: Plus,
          },
          {
            id: 'faro-leader',
            label: 'Asignar Líder',
            href: '/evangelism/faro/groups?mode=leader',
            icon: UserPlus,
          },
          {
            id: 'faro-assistant',
            label: 'Asignar Colíder',
            href: '/evangelism/faro/groups?mode=assistant',
            icon: Shield,
          },
          {
            id: 'faro-host',
            label: 'Asignar Anfitrión',
            href: '/evangelism/faro/groups?mode=host',
            icon: Home,
          },
          {
            id: 'faro-members',
            label: 'Asignar Miembros',
            href: '/evangelism/faro/groups?mode=members',
            icon: Users,
          },
          {
            id: 'faro-monitor',
            label: 'Monitoreo',
            href: '/evangelism/faro/groups?mode=monitor',
            icon: Activity,
          },
        ],
      },
    ],
  },
  academy: {
    title: 'Academia',
    sections: [
      {
        title: 'Formación',
        items: [
          {
            id: 'aca-dashboard',
            label: 'Resumen',
            href: '/academy',
            icon: LayoutDashboard,
          },
          {
            id: 'aca-courses',
            label: 'Gestión Cursos',
            href: '/academy/courses',
            icon: BookOpen,
          },
          {
            id: 'aca-students',
            label: 'Estudiantes',
            href: '/academy/students',
            icon: Users,
          },
          {
            id: 'aca-teachers',
            label: 'Facilitadores',
            href: '/academy/teachers',
            icon: GraduationCap,
          },
        ],
      },
    ],
  },
  finances: {
    title: 'Finanzas',
    sections: [
      {
        title: 'Reportes',
        items: [
          {
            id: 'fin-home',
            label: 'Resumen',
            href: '/finances',
            icon: LayoutDashboard,
          },
          {
            id: 'fin-transparency',
            label: 'Transparencia',
            href: '/finances/transparency',
            icon: FileText,
          },
        ],
      },
    ],
  },
  inbox: {
    title: 'Bandeja',
    sections: [
      {
        title: 'Filtros',
        items: [
          { id: 'inbox-all', label: 'Todo', href: '/inbox', icon: Inbox },
          {
            id: 'inbox-mentions',
            label: 'Menciones',
            href: '/inbox#menciones',
            icon: MessageCircle,
          },
          {
            id: 'inbox-tasks',
            label: 'Tareas',
            href: '/inbox#tareas',
            icon: CheckSquare,
          },
          { id: 'inbox-ai', label: 'MESH AI', href: '/inbox#ai', icon: Bot },
        ],
      },
    ],
  },
  cms: {
    title: 'Sitio Web',
    sections: [
      {
        title: 'Contenido',
        items: [
          {
            id: 'cms-home',
            label: 'Inicio CMS',
            href: '/cms',
            icon: LayoutDashboard,
          },
          {
            id: 'cms-pages',
            label: 'Páginas',
            href: '/cms/pages',
            icon: FileText,
          },
          {
            id: 'cms-menus',
            label: 'Menús del sitio',
            href: '/cms/menus',
            icon: Link2,
          },
          {
            id: 'cms-testimonials',
            label: 'Testimonios',
            href: '/cms/testimonials',
            icon: MessageCircle,
          },
          {
            id: 'cms-content',
            label: 'Landing Hero',
            href: '/cms/content',
            icon: FileText,
          },
          {
            id: 'cms-events',
            label: 'Eventos públicos',
            href: '/cms/events',
            icon: Calendar,
          },
        ],
      },
    ],
  },
  wiki: {
    title: 'Conocimiento',
    sections: [
      {
        title: 'Espacios',
        items: [
          {
            id: 'wiki-home',
            label: 'Inicio Wiki',
            href: '/wiki',
            icon: LayoutDashboard,
          },
          {
            id: 'wiki-docs',
            label: 'Documentos',
            href: '/wiki/docs',
            icon: FileText,
          },
        ],
      },
    ],
  },
  groups: {
    title: 'Comunidad',
    sections: [
      {
        title: 'Células',
        items: [
          {
            id: 'groups-all',
            label: 'Casas de Bendición',
            href: '/groups',
            icon: Home,
          },
          {
            id: 'groups-family',
            label: 'Núcleos Familiares',
            href: '/groups/family',
            icon: Users,
          },
          {
            id: 'groups-crm',
            label: 'Directorio CRM',
            href: '/crm',
            icon: ShieldCheck,
          },
        ],
      },
    ],
  },
  'spiritual-life': {
    title: 'Vida Espiritual',
    sections: [
      {
        title: 'Mi Caminar',
        items: [
          {
            id: 'sl-home',
            label: 'Panel Espiritual',
            href: '/spiritual-life',
            icon: BookOpen,
          },
          {
            id: 'sl-tl',
            label: 'Línea de Tiempo',
            href: '/spiritual-life/timeline',
            icon: Calendar,
          },
          {
            id: 'sl-certs',
            label: 'Mis Certificados',
            href: '/spiritual-life/certificates',
            icon: FileText,
          },
        ],
      },
      {
        title: 'Formación',
        items: [
          {
            id: 'sl-academy',
            label: 'Academia CCF',
            href: '/academy',
            icon: BookOpen,
          },
        ],
      },
    ],
  },
};
