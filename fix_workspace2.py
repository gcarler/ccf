import sys
content = open('frontend/src/components/WorkspaceLayout.tsx', 'r', encoding='utf-8').read()

target = '    finances: {\n        title: "Finanzas",\n'

insertion = '''    evangelism: {
        title: "Evangelismo & Eventos",
        sections: [
            {
                title: "Estrategia",
                items: [
                    { id: 'ev-events',    label: 'Eventos',       href: '/evangelism/events',    icon: Calendar },
                    { id: 'ev-faro',      label: 'Faro: Panel',  href: '/evangelism/faro',      icon: Activity },
                    { id: 'ev-faro-groups', label: 'Faro: Grupos',  href: '/evangelism/faro/groups', icon: Home },
                    { id: 'ev-scanner',   label: 'Escáner ASST',  href: '/evangelism/scanner',   icon: Scan },
                ]
            }
        ]
    },
    academy: {
        title: "Academia",
        sections: [
            {
                title: "Formación",
                items: [
                    { id: 'aca-dashboard',  label: 'Resumen',        href: '/academy',               icon: LayoutDashboard },
                    { id: 'aca-courses',    label: 'Gestión Cursos', href: '/academy/courses',       icon: BookOpen },
                    { id: 'aca-students',   label: 'Estudiantes',    href: '/academy/students',      icon: Users },
                    { id: 'aca-teachers',   label: 'Facilitadores',  href: '/academy/teachers',      icon: GraduationCap },
                ]
            }
        ]
    },
'''

if target in content:
    content = content.replace(target, insertion + target)
    open('frontend/src/components/WorkspaceLayout.tsx', 'w', encoding='utf-8').write(content)
    print('Inserted evangelism & academy back')
else:
    print('Target not found')
