f = open('frontend/src/components/WorkspaceLayout.tsx', encoding='utf-8').read()

lines = f.split('\n')
out = []
for line in lines:
    if "id: 'crm-events'" in line:
        continue
    if "id: 'crm-events-analytics'" in line:
        continue
    if "id: 'crm-faro'" in line:
        continue
    if "id: 'crm-scanner'" in line:
        continue
    
    if 'title: "Servicio y Vida"' in line:
        evang_block = """            {
                title: "Evangelismo & Eventos",
                items: [
                    { id: 'ev-events',    label: 'Eventos',           href: '/evangelism/events',    icon: Calendar },
                    { id: 'ev-analytics', label: 'Dashboard Eventos', href: '/evangelism/events/analytics', icon: BarChart3 },
                    { id: 'ev-faro',      label: 'Faro en Casa',      href: '/evangelism/faro',      icon: Home },
                    { id: 'ev-scanner',   label: 'Escáner ASST',      href: '/evangelism/scanner',   icon: Scan },
                ]
            },"""
        out.append(evang_block)
    
    out.append(line)

open('frontend/src/components/WorkspaceLayout.tsx', 'w', encoding='utf-8').write('\n'.join(out))
