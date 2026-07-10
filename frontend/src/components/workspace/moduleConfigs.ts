import {
  Activity,
  AlertTriangle,
  BookOpen,
  Bot,
  Calendar,
  CheckSquare,
  Contact,
  FileText,
  FolderTree,
  Globe,
  GraduationCap,
  Heart,
  Home,
  ImageIcon,
  Inbox,
  KanbanSquare,
  Layers3,
  Layout,
  LayoutDashboard,
  Link2,
  Mail,
  MessageCircle,
  PackageOpen,
  Palette,
  PanelsTopLeft,
  PieChart,
  Puzzle,
  RotateCcw,
  Scan,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  UserPlus,
  Users,
  Webhook,
  Zap,
  Plus,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface ModuleNavItem {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
}

interface ModuleNavSection {
  title: string;
  items: ModuleNavItem[];
}

interface ModuleConfig {
  title: string;
  sections: ModuleNavSection[];
}

export const MODULE_CONFIGS: Record<string, ModuleConfig> = {
  projects: {
    title: 'Portfolio',
    sections: [
      {
        title: 'Gestión',
        items: [
          {
            id: 'projects-home',
            label: 'Portfolio',
            href: '/plataforma/projects',
            icon: Layout,
          },
          {
            id: 'projects-tasks',
            label: 'Mis Tareas',
            href: '/plataforma/tasks',
            icon: CheckSquare,
          },
          {
            id: 'projects-team',
            label: 'Equipo',
            href: '/plataforma/projects/team',
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
            href: '/plataforma/calendar',
            icon: Calendar,
          },
          {
            id: 'projects-auto',
            label: 'Automatizaciones',
            href: '/plataforma/projects/automations',
            icon: Zap,
          },
          {
            id: 'projects-messages',
            label: 'Mensajes',
            href: '/plataforma/messages',
            icon: MessageCircle,
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
            href: '/plataforma/tasks',
            icon: CheckSquare,
          },
          {
            id: 'tasks-calendar',
            label: 'Calendario',
            href: '/plataforma/calendar',
            icon: Calendar,
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
            href: '/plataforma/calendar',
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
            href: '/plataforma/crm/analytics',
            icon: PieChart,
          },
        ],
      },
      {
        title: 'Directorio Pastoral',
        items: [
          {
            id: 'crm-personas',
            label: 'Personas',
            href: '/plataforma/crm/personas',
            icon: Users,
          },
          {
            id: 'crm-groups',
            label: 'Grupos',
            href: '/plataforma/crm/groups',
            icon: Home,
          },
          {
            id: 'crm-contacts',
            label: 'Contactos/Leads',
            href: '/plataforma/crm/contacts',
            icon: UserPlus,
          },
          {
            id: 'crm-volunteers',
            label: 'Voluntariado',
            href: '/plataforma/crm/volunteers',
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
            href: '/plataforma/crm/pipeline',
            icon: KanbanSquare,
          },
          {
            id: 'crm-counseling',
            label: 'Consejería',
            href: '/plataforma/crm/counseling',
            icon: Heart,
          },
          {
            id: 'crm-prayers',
            label: 'Muro de Oración',
            href: '/plataforma/crm/prayers',
            icon: MessageCircle,
          },
          {
            id: 'crm-tasks',
            label: 'Tareas Asignadas',
            href: '/plataforma/crm/tasks',
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
            href: '/plataforma/crm/messaging',
            icon: Mail,
          },
          {
            id: 'crm-mycard',
            label: 'Mi Carnet',
            href: '/plataforma/crm/my-card',
            icon: Contact,
          },
          {
            id: 'crm-settings',
            label: 'Configuración',
            href: '/plataforma/crm/settings',
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
            href: '/plataforma/evangelism/events',
            icon: Calendar,
          },
          {
            id: 'ev-groups',
            label: 'Panel de Grupo',
            href: '/plataforma/evangelism/groups',
            icon: Activity,
          },
          {
            id: 'ev-site-groups',
            label: 'Grupos',
            href: '/plataforma/evangelism/groups/groups',
            icon: Home,
          },
          {
            id: 'ev-scanner',
            label: 'Escáner ASST',
            href: '/plataforma/evangelism/scanner',
            icon: Scan,
          },
        ],
      },
      {
        title: 'Gestión de Grupos',
        items: [
          {
            id: 'groups-create',
            label: 'Crear Nuevo',
            href: '/plataforma/evangelism/groups/groups?mode=create',
            icon: Plus,
          },
          {
            id: 'groups-leader',
            label: 'Asignar Líder',
            href: '/plataforma/evangelism/groups/groups?mode=leader',
            icon: UserPlus,
          },
          {
            id: 'groups-assistant',
            label: 'Asignar Colíder',
            href: '/plataforma/evangelism/groups/groups?mode=assistant',
            icon: Shield,
          },
          {
            id: 'groups-host',
            label: 'Asignar Anfitrión',
            href: '/plataforma/evangelism/groups/groups?mode=host',
            icon: Home,
          },
          {
            id: 'groups-personas',
            label: 'Asignar Personas',
            href: '/plataforma/evangelism/groups/groups?mode=personas',
            icon: Users,
          },
          {
            id: 'groups-monitor',
            label: 'Monitoreo',
            href: '/plataforma/evangelism/groups/groups?mode=monitor',
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
            href: '/plataforma/academy',
            icon: LayoutDashboard,
          },
          {
            id: 'aca-courses',
            label: 'Gestión Cursos',
            href: '/plataforma/academy/courses',
            icon: BookOpen,
          },
          {
            id: 'aca-students',
            label: 'Estudiantes',
            href: '/plataforma/academy/students',
            icon: Users,
          },
          {
            id: 'aca-teachers',
            label: 'Facilitadores',
            href: '/plataforma/academy/teachers',
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
            href: '/plataforma/finances',
            icon: LayoutDashboard,
          },
          {
            id: 'fin-transparency',
            label: 'Transparencia',
            href: '/plataforma/finances/transparency',
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
          { id: 'inbox-all', label: 'Todo', href: '/plataforma/inbox', icon: Inbox },
          {
            id: 'inbox-mentions',
            label: 'Menciones',
            href: '/plataforma/inbox#menciones',
            icon: MessageCircle,
          },
          {
            id: 'inbox-tasks',
            label: 'Tareas',
            href: '/plataforma/inbox#tareas',
            icon: CheckSquare,
          },
          { id: 'inbox-ai', label: 'MESH AI', href: '/plataforma/inbox#ai', icon: Bot },
        ],
      },
    ],
  },
  cms: {
    title: 'Sitio Web',
    sections: [
      {
        title: 'Principal',
        items: [
          { id: 'cms-home', label: 'Inicio CMS', href: '/plataforma/cms', icon: LayoutDashboard },
          { id: 'cms-pages', label: 'Páginas', href: '/plataforma/cms/pages', icon: FileText },
          { id: 'cms-builder', label: 'Builder', href: '/plataforma/cms/builder', icon: PanelsTopLeft },
          { id: 'cms-media', label: 'Media', href: '/plataforma/cms/media', icon: ImageIcon },
          { id: 'cms-media-folders', label: 'Carpetas Media', href: '/plataforma/cms/media-folders', icon: FolderTree },
        ],
      },
      {
        title: 'Contenido',
        items: [
          { id: 'cms-testimonials', label: 'Testimonios', href: '/plataforma/cms/testimonials', icon: MessageCircle },
          { id: 'cms-menus', label: 'Menús del sitio', href: '/plataforma/cms/menus', icon: Link2 },
          { id: 'cms-posts', label: 'Posts / Blog', href: '/plataforma/cms/posts', icon: BookOpen },
          { id: 'cms-categories', label: 'Categorías', href: '/plataforma/cms/categories', icon: Inbox },
          { id: 'cms-tags', label: 'Etiquetas', href: '/plataforma/cms/tags', icon: CheckSquare },
          { id: 'cms-resources', label: 'Recursos', href: '/plataforma/cms/resources', icon: PackageOpen },
        ],
      },
      {
        title: 'Configuración',
        items: [
          { id: 'cms-branding', label: 'Logo & Branding', href: '/plataforma/cms/branding', icon: Palette },
          { id: 'cms-themes', label: 'Temas', href: '/plataforma/cms/themes', icon: Palette },
          { id: 'cms-sites', label: 'Sitios', href: '/plataforma/cms/sites', icon: Globe },
          { id: 'cms-pastoral-team', label: 'Equipo Pastoral', href: '/plataforma/cms/pastoral-team', icon: Users },
          { id: 'cms-section-types', label: 'Tipos de Sección', href: '/plataforma/cms/section-types', icon: Layers3 },
          { id: 'cms-custom-types', label: 'Tipos Custom', href: '/plataforma/cms/custom-types', icon: Puzzle },
          { id: 'cms-glossary', label: 'Glosario', href: '/plataforma/cms/glossary', icon: FileText },
        ],
      },
      {
        title: 'Sistema',
        items: [
          { id: 'cms-audit', label: 'Auditoría', href: '/plataforma/cms/audit', icon: Shield },
          { id: 'cms-notifications', label: 'Notificaciones', href: '/plataforma/cms/notifications', icon: Mail },
          { id: 'cms-webhooks', label: 'Webhooks', href: '/plataforma/cms/webhooks', icon: Webhook },
          { id: 'cms-search-admin', label: 'Búsqueda', href: '/plataforma/cms/search-admin', icon: Search },
          { id: 'cms-sessions', label: 'Sesiones', href: '/plataforma/cms/sessions', icon: Shield },
          { id: 'cms-redirects', label: 'Redirecciones', href: '/plataforma/cms/redirects', icon: RotateCcw },
          { id: 'cms-broken-links', label: 'Links Rotos', href: '/plataforma/cms/broken-links', icon: AlertTriangle },
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
            href: '/plataforma/wiki',
            icon: LayoutDashboard,
          },
          {
            id: 'wiki-docs',
            label: 'Documentos',
            href: '/plataforma/wiki/docs',
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
            href: '/plataforma/community/grupos',
            icon: Home,
          },
          {
            id: 'groups-family',
            label: 'Núcleos Familiares',
            href: '/plataforma/groups/family',
            icon: Users,
          },
          {
            id: 'groups-crm',
            label: 'Directorio CRM',
            href: '/plataforma/crm',
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
            href: '/plataforma/spiritual-life',
            icon: BookOpen,
          },
          {
            id: 'sl-tl',
            label: 'Línea de Tiempo',
            href: '/plataforma/spiritual-life/timeline',
            icon: Calendar,
          },
          {
            id: 'sl-certs',
            label: 'Mis Certificados',
            href: '/plataforma/spiritual-life/certificates',
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
            href: '/plataforma/academy',
            icon: BookOpen,
          },
        ],
      },
    ],
  },
};
