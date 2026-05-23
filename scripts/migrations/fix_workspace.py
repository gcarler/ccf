import sys

with open("frontend/src/components/WorkspaceLayout.tsx", "r", encoding="utf-8") as f:
    content = f.read()

target = """                    { id: 'ev-events',    label: 'Eventos',       href: '/evangelism/events',    icon: Calendar },
                    { id: 'ev-faro',      label: 'Faro en Casa',  href: '/evangelism/faro',      icon: Home },
                    { id: 'ev-scanner',   label: 'Escáner ASST',  href: '/evangelism/scanner',   icon: Scan },"""

replacement = """                    { id: 'ev-events',    label: 'Eventos',       href: '/evangelism/events',    icon: Calendar },
                    { id: 'ev-faro',      label: 'Faro: Panel',  href: '/evangelism/faro',      icon: Activity },
                    { id: 'ev-faro-groups', label: 'Faro: Grupos',  href: '/evangelism/faro/groups', icon: Home },
                    { id: 'ev-scanner',   label: 'Escáner ASST',  href: '/evangelism/scanner',   icon: Scan },"""

if target in content:
    content = content.replace(target, replacement)
    with open(
        "frontend/src/components/WorkspaceLayout.tsx", "w", encoding="utf-8"
    ) as f:
        f.write(content)
    print("Fixed WorkspaceLayout.tsx")
else:
    print("Target not found")
