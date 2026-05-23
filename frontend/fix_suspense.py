import re

with open(
    "d:/ccf/frontend/src/app/evangelism/faro/groups/page.tsx", "r", encoding="utf-8"
) as f:
    content = f.read()

if "import React, { Suspense," not in content and "import { Suspense }" not in content:
    content = content.replace(
        "import React, { useState", "import React, { useState, Suspense"
    )

content = content.replace(
    "export default function FaroGroupsPage()", "function FaroGroupsContent()"
)

suspense_wrapper = """

export default function FaroGroupsPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center text-slate-500">Cargando grupos...</div>}>
            <FaroGroupsContent />
        </Suspense>
    );
}
"""
content += suspense_wrapper

with open(
    "d:/ccf/frontend/src/app/evangelism/faro/groups/page.tsx", "w", encoding="utf-8"
) as f:
    f.write(content)

print("Done")
