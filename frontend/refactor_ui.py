with open(
    "d:/ccf/frontend/src/app/evangelism/faro/groups/page.tsx", "r", encoding="utf-8"
) as f:
    content = f.read()

# 1. Replace the outer container and list side container
content = content.replace(
    '<div className="flex h-full gap-0">',
    '<div className="flex h-full gap-4 p-4 lg:p-6 bg-slate-50/50 dark:bg-[#1a1b1e]/50">',
)

content = content.replace(
    "<div className={`flex flex-col min-w-0 border-r border-slate-100 dark:border-white/5 transition-all ${showPanel ? 'w-72 shrink-0' : 'flex-1'}`}>",
    "<div className={`flex flex-col min-w-0 bg-white dark:bg-[#252528] rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden transition-all duration-300 ${showPanel ? 'w-[400px] shrink-0' : 'flex-1'}`}>",
)

# 2. Replace the list container to use a grid when showPanel is false
content = content.replace(
    '<div className="flex-1 overflow-y-auto py-2 scrollbar-thin">',
    "<div className={`flex-1 overflow-y-auto p-4 scrollbar-thin ${!showPanel ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 content-start' : 'flex flex-col gap-2'}`}>",
)

# 3. Replace the button styling
old_button_class = """className={`w-full text-left px-4 py-3 border-l-2 transition-all ${
                                        isActive
                                            ? 'bg-blue-50 dark:bg-blue-900/10 border-l-blue-600'
                                            : 'border-l-transparent hover:bg-slate-50 dark:hover:bg-white/3'
                                    }`}"""

new_button_class = """className={`w-full text-left p-4 rounded-xl border transition-all duration-200 ${
                                        isActive
                                            ? 'bg-blue-50/80 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700 ring-1 ring-blue-500 shadow-sm'
                                            : 'bg-white dark:bg-[#2a2b2f] border-slate-200 dark:border-white/5 hover:border-blue-400/40 hover:shadow-md'
                                    }`}"""

content = content.replace(old_button_class, new_button_class)

# 4. Detail Panel Container
old_detail_panel = """{showPanel ? (
                    <div className="flex-1 bg-white dark:bg-[#1e1f21] flex flex-col overflow-hidden">"""

new_detail_panel = """{showPanel ? (
                    <div className="flex-1 bg-white dark:bg-[#252528] rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm flex flex-col overflow-hidden animate-in fade-in slide-in-from-right-4 duration-300">"""

content = content.replace(old_detail_panel, new_detail_panel)

# Also remove the border-b from the detail header since the card itself is clean
content = content.replace(
    '<div className="px-8 py-5 border-b border-slate-100 dark:border-white/5 flex items-center justify-between shrink-0">',
    '<div className="px-8 py-6 border-b border-slate-100/80 dark:border-white/5 flex items-center justify-between shrink-0 bg-slate-50/50 dark:bg-white/[0.02]">',
)

with open(
    "d:/ccf/frontend/src/app/evangelism/faro/groups/page.tsx", "w", encoding="utf-8"
) as f:
    f.write(content)

print("Done")
