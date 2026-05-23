f = open('frontend/src/components/WorkspaceLayout.tsx', encoding='utf-8')
c = f.read()
f.close()

# Update the Faro en Casa nav item to point to the new dedicated page
c = c.replace(
    "{ id: 'crm-groups',    label: 'Faro en Casa',      href: '/crm/groups',    icon: Home },",
    "{ id: 'crm-faro',      label: 'Faro en Casa',      href: '/crm/faro',      icon: Home },"
)

open('frontend/src/components/WorkspaceLayout.tsx', 'w', encoding='utf-8').write(c)
print("Sidebar updated to /crm/faro")
