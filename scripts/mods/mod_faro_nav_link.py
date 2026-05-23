f = open("frontend/src/app/crm/faro/page.tsx", encoding="utf-8")
c = f.read()
f.close()

# Add useRouter import
c = c.replace(
    "import React, { useState, useEffect } from 'react';",
    "import React, { useState, useEffect } from 'react';\nimport { useRouter } from 'next/navigation';",
)

# Add router hook
c = c.replace(
    "    const { token } = useAuth();",
    "    const { token } = useAuth();\n    const router = useRouter();",
)

# Make per_faro rows clickable (the table row)
c = c.replace(
    '<tr key={row.glory_house_id} className="border-b border-slate-50 dark:border-white/5 last:border-0 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">',
    '<tr key={row.glory_house_id} onClick={() => router.push(`/crm/faro/${row.glory_house_id}`)} className="border-b border-slate-50 dark:border-white/5 last:border-0 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer">',
)

open("frontend/src/app/crm/faro/page.tsx", "w", encoding="utf-8").write(c)
print("Faro page updated with router navigation")
