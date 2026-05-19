import sys

with open('frontend/src/components/WorkspaceLayout.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

crm_old = """    crm: {
        title: "Comunidad CRM",
        sections: [
            {
                title: "Actividad y Mtricas",
                items: [
                    { id: 'crm-analytics', label: 'Panel Analtico', href: '/crm/analytics', icon: PieChart }
                ]
            },
            {
                title: "Directorio Pastoral",
                items: [
                    { id: 'crm-members',    label: 'Miembros',          href: '/crm/members',    icon: Users },
                    { id: 'crm-groups',     label: 'Casas de Gloria',   href: '/crm/groups',     icon: Home },
                    { id: 'crm-contacts',   label: 'Contactos/Leads',   href: '/crm/contacts',   icon: UserPlus },
                    { id: 'crm-volunteers', label: 'Voluntariado',      href: '/crm/volunteers', icon: ShieldCheck },
                ]
            },
            {
                title: "Consolidacin",
                items: [
                    { id: 'crm-pipeline',   label: 'Pipeline pastoral', href: '/crm/pipeline',   icon: KanbanSquare },
                    { id: 'crm-counseling', label: 'Consejera',        href: '/crm/counseling', icon: Heart },
                    { id: 'crm-prayers',    label: 'Muro de Oracin',   href: '/crm/prayers',    icon: MessageCircle },
                    { id: 'crm-tasks',      label: 'Tareas Asignadas',  href: '/crm/tasks',      icon: CheckSquare },
                ]
            },
            {
                title: "Herramientas",
                items: [
                    { id: 'crm-events',    label: 'Eventos',       href: '/crm/events',    icon: Calendar },
                    { id: 'crm-scanner',   label: 'Escner ASST',  href: '/crm/scanner',   icon: Scan },
                    { id: 'crm-messaging', label: 'Mensajera',    href: '/crm/messaging', icon: Mail },
                    { id: 'crm-mycard',    label: 'Mi Carnet',     href: '/crm/my-card',   icon: Contact },
                    { id: 'crm-settings',  label: 'Configuracin', href: '/crm/settings',  icon: Settings },
                ]
            }
        ]
    },"""

crm_new = """    crm: {
        title: "Sistema Pastoral",
        sections: [
            {
                title: "Consolidacin (CRM)",
                items: [
                    { id: 'crm-members',    label: 'Miembros',          href: '/crm/members',    icon: Users },
                    { id: 'crm-contacts',   label: 'Contactos/Leads',   href: '/crm/contacts',   icon: UserPlus },
                    { id: 'crm-pipeline',   label: 'Embudos',           href: '/crm/pipeline',   icon: KanbanSquare },
                    { id: 'crm-counseling', label: 'Consejera',        href: '/crm/counseling', icon: Heart },
                    { id: 'crm-tasks',      label: 'Tareas Pastorales', href: '/crm/tasks',      icon: CheckSquare },
                ]
            },
            {
                title: "Evangelismo",
                items: [
                    { id: 'crm-events',    label: 'Eventos',           href: '/crm/events',    icon: Calendar },
                    { id: 'crm-groups',    label: 'Faro en Casa',      href: '/crm/groups',    icon: Home },
                    { id: 'crm-scanner',   label: 'Escner ASST',      href: '/crm/scanner',   icon: Scan },
                ]
            },
            {
                title: "Servicio y Vida",
                items: [
                    { id: 'crm-volunteers', label: 'Voluntariado',      href: '/crm/volunteers', icon: ShieldCheck },
                    { id: 'crm-prayers',    label: 'Muro de Oracin',   href: '/crm/prayers',    icon: MessageCircle },
                    { id: 'crm-messaging',  label: 'Mensajera',        href: '/crm/messaging',  icon: Mail },
                    { id: 'crm-mycard',     label: 'Mi Carnet',         href: '/crm/my-card',    icon: Contact },
                ]
            }
        ]
    },"""

c = c.replace(crm_old, crm_new)

with open('frontend/src/components/WorkspaceLayout.tsx', 'w', encoding='utf-8') as f:
    f.write(c)

print("Sidebar updated")
