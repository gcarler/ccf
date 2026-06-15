import {
  LayoutDashboard,
  PieChart,
  Inbox,
  CheckCircle2,
  Target,
  UserPlus,
  Mail,
  Heart,
  MessageCircle,
  Home as HouseIcon,
  Users,
  ShieldCheck,
  QrCode,
  Settings,
  BookOpen,
} from 'lucide-react';

export const CRM_SIDEBAR_SECTIONS = [
  {
    title: 'General',
    items: [
      { id: 'crm-dashboard', label: 'Dashboard', icon: LayoutDashboard, href: '/plataforma/crm' },
      { id: 'crm-analytics', label: 'Analítica', icon: PieChart, href: '/plataforma/crm/analytics' },
      { id: 'crm-messaging', label: 'Mensajería', icon: Inbox, href: '/plataforma/crm/messaging' },
      { id: 'crm-resources', label: 'Recursos', icon: BookOpen, href: '/plataforma/crm/resources' },
      { id: 'crm-tasks', label: 'Tareas', icon: CheckCircle2, href: '/plataforma/crm/tasks' },
    ],
  },
  {
    title: 'Ministerio',
    items: [
      { id: 'crm-pipeline', label: 'Consolidación', icon: Target, href: '/plataforma/crm/pipeline' },
      { id: 'crm-contacts', label: 'Leads / Contactos', icon: UserPlus, href: '/plataforma/crm/contacts' },
      { id: 'crm-newsletter', label: 'Newsletter CRM', icon: Mail, href: '/plataforma/crm/newsletter-leads' },
      { id: 'crm-counseling', label: 'Consejería', icon: Heart, href: '/plataforma/crm/counseling' },
      { id: 'crm-prayers', label: 'Muro de Oración', icon: MessageCircle, href: '/plataforma/crm/prayers' },
      { id: 'crm-groups', label: 'Grupos', icon: HouseIcon, href: '/plataforma/crm/groups' },
    ],
  },
  {
    title: 'Comunidad',
    items: [
      { id: 'crm-personas', label: 'Personas', icon: Users, href: '/plataforma/crm/personas' },
      { id: 'crm-volunteers', label: 'Servidores', icon: ShieldCheck, href: '/plataforma/crm/volunteers' },
    ],
  },
  {
    title: 'Personal',
    items: [
      { id: 'crm-card', label: 'Mi Carnet', icon: QrCode, href: '/plataforma/crm/my-card' },
      { id: 'crm-settings', label: 'Configuración', icon: Settings, href: '/plataforma/crm/settings' },
    ],
  },
];
