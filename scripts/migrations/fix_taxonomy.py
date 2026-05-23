import codecs
import re

with codecs.open('frontend/src/components/WorkspaceLayout.tsx', 'r', 'utf-8') as f:
    c = f.read()

replacement = '''    crm: {
        title: "Sistema Pastoral",
        sections: [
            {
                title: "Consolidación (CRM)",
                items: [
                    { id: 'crm-members',    label: 'Miembros',          href: '/crm/members',    icon: Users },
                    { id: 'crm-contacts',   label: 'Contactos/Leads',   href: '/crm/contacts',   icon: UserPlus },
                    { id: 'crm-pipeline',   label: 'Embudos',           href: '/crm/pipeline',   icon: KanbanSquare },
                    { id: 'crm-counseling', label: 'Consejería',        href: '/crm/counseling', icon: Heart },
                    { id: 'crm-tasks',      label: 'Tareas Pastorales', href: '/crm/tasks',      icon: CheckSquare },
                ]
            },
            {
                title: "Evangelismo",
                items: [
                    { id: 'crm-events',    label: 'Eventos',           href: '/crm/events',    icon: Calendar },
                    { id: 'crm-groups',    label: 'Faro en Casa',      href: '/crm/groups',    icon: Home },
                    { id: 'crm-scanner',   label: 'Escáner ASST',      href: '/crm/scanner',   icon: Scan },
                ]
            },
            {
                title: "Servicio y Vida",
                items: [
                    { id: 'crm-volunteers', label: 'Voluntariado',      href: '/crm/volunteers', icon: ShieldCheck },
                    { id: 'crm-prayers',    label: 'Muro de Oración',   href: '/crm/prayers',    icon: MessageCircle },
                    { id: 'crm-messaging',  label: 'Mensajería',        href: '/crm/messaging',  icon: Mail },
                    { id: 'crm-mycard',     label: 'Mi Carnet',         href: '/crm/my-card',    icon: Contact },
                ]
            }
        ]
    },
    cms: {'''

c = re.sub(r'crm: \{.*?^\s*cms: \{', replacement, c, flags=re.DOTALL | re.MULTILINE)

with codecs.open('frontend/src/components/WorkspaceLayout.tsx', 'w', 'utf-8') as f:
    f.write(c)

print('Done')
