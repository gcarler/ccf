import codecs

with codecs.open("frontend/src/components/WorkspaceLayout.tsx", "r", "utf-8") as f:
    c = f.read()

import_old = "import { LayoutDashboard, Users, UserSquare2, PhoneCall, ListTodo, Calendar, Home, Scan, ShieldCheck, MessageCircle, Mail, Contact } from 'lucide-react';"
import_new = "import { LayoutDashboard, Users, UserSquare2, PhoneCall, ListTodo, Calendar, Home, Scan, ShieldCheck, MessageCircle, Mail, Contact, BarChart3 } from 'lucide-react';"
c = c.replace(import_old, import_new)

nav_old = """                    { id: 'crm-events',    label: 'Eventos',           href: '/crm/events',    icon: Calendar },
                    { id: 'crm-groups',    label: 'Faro en Casa',      href: '/crm/groups',    icon: Home },
                    { id: 'crm-scanner',   label: 'Escáner ASST',      href: '/crm/scanner',   icon: Scan },
                ]"""
nav_new = """                    { id: 'crm-events',    label: 'Eventos',           href: '/crm/events',    icon: Calendar },
                    { id: 'crm-events-analytics', label: 'Dashboard Eventos', href: '/crm/events/analytics', icon: BarChart3 },
                    { id: 'crm-groups',    label: 'Faro en Casa',      href: '/crm/groups',    icon: Home },
                    { id: 'crm-scanner',   label: 'Escáner ASST',      href: '/crm/scanner',   icon: Scan },
                ]"""
c = c.replace(nav_old, nav_new)

with codecs.open("frontend/src/components/WorkspaceLayout.tsx", "w", "utf-8") as f:
    f.write(c)

print("Sidebar updated")
