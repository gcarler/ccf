import re

with open('d:/ccf/frontend/src/app/evangelism/faro/groups/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add imports
if 'useSidebarLayers' not in content:
    content = content.replace(
        "import { apiFetch } from '@/lib/http';",
        "import { apiFetch } from '@/lib/http';\nimport { useSidebarLayers } from '@/context/SidebarLayerContext';"
    )

# 2. Add hook to component
if 'const { pushSidebarPanel' not in content:
    content = content.replace(
        "const searchParams = useSearchParams();",
        "const searchParams = useSearchParams();\n  const { pushSidebarPanel, resetSidebarStack } = useSidebarLayers();"
    )

# 3. Extract the list HTML
list_start = content.find('{/* List Side */}')
list_end = content.find('{/* Detail/Edit Panel */}')

list_html = content[list_start:list_end]

# We need to build the useEffect block
use_effect_block = """
  // PUSH LIST TO SIDEBAR 2
  useEffect(() => {
    pushSidebarPanel({
      id: 'faro-groups-list',
      title: 'Grupos Faro',
      replaceAll: true,
      content: (
        <div className="flex flex-col h-full">
          <div className="px-5 pt-3 pb-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Buscar Grupo</span>
              <button
                onClick={() => {
                  setIsCreating(true);
                  setSelectedHouse(null);
                  setSelectedMemberIds(new Set());
                  setFormData({ capacity: 15, status: 'Activo' });
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg size-7 flex items-center justify-center transition-all shadow-sm active:scale-95"
              >
                <Plus size={14} />
              </button>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Buscar por nombre o zona..."
                className="w-full bg-slate-100 dark:bg-white/5 border border-transparent rounded-xl py-2 pl-9 pr-3 text-[13px] font-medium focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 outline-none transition-all"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 pb-4 scrollbar-thin flex flex-col gap-1">
            {loading ? (
              <div className="py-12 text-center text-slate-400">
                <Activity className="animate-spin mx-auto opacity-50" />
              </div>
            ) : filteredHouses.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-sm">
                No se encontraron grupos
              </div>
            ) : (
              filteredHouses.map(h => {
                const isActive = selectedHouse?.id === h.id;
                return (
                  <button
                    key={h.id}
                    onClick={async () => {
                      setIsCreating(false);
                      try {
                        const detail = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${h.id}`, { token });
                        setSelectedHouse(detail);
                        setFormData(detail);
                        setSelectedMemberIds(new Set(detail.base_attendee_ids || detail.base_attendees?.map(m => m.member_id) || []));
                      } catch {
                        setSelectedHouse(h);
                        setFormData(h);
                        setSelectedMemberIds(new Set());
                      }
                    }}
                    className={`w-full text-left px-3 py-2.5 rounded-xl border transition-all duration-200 ${
                      isActive
                        ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 shadow-sm'
                        : 'bg-transparent border-transparent hover:bg-slate-100 dark:hover:bg-white/5'
                    }`}
                  >
                    <p className={`text-[13px] font-bold truncate leading-tight ${isActive ? 'text-blue-700 dark:text-blue-400' : 'text-slate-800 dark:text-white'}`}>
                      {h.name}
                    </p>
                    <div className="mt-1 flex items-center justify-between">
                      <p className="text-[10px] font-medium text-slate-400 truncate">
                        {h.zone || 'Sin zona'}
                      </p>
                      {h.leader_id && (
                        <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-blue-100/50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 shrink-0">
                          {getMemberName(h.leader_id).split(' ')[0]}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )
    });
  }, [pushSidebarPanel, filteredHouses, searchQuery, loading, selectedHouse, isCreating, mode, token]);

  // Clean up sidebar when unmounting
  useEffect(() => {
    return () => resetSidebarStack();
  }, [resetSidebarStack]);

"""

# Insert useEffect before return
content = content.replace('  return (\n    <EvangelismShell', use_effect_block + '\n  return (\n    <EvangelismShell')

# Remove the old list HTML
content = content.replace(list_html, '')

# Now simplify the main return area since it only renders the detail panel or an empty state
# We replace: <div className="flex h-full gap-4 p-4 lg:p-6 bg-slate-50/50 dark:bg-[#1a1b1e]/50">
# With a cleaner container that takes up the full width.
content = content.replace(
    '<div className="flex h-full gap-4 p-4 lg:p-6 bg-slate-50/50 dark:bg-[#1a1b1e]/50">',
    '<div className="flex h-full p-4 lg:p-6 bg-slate-50/50 dark:bg-[#1a1b1e]/50">'
)

# And if `showPanel` is false, it renders the empty state. Right now, there is an else branch for showPanel.
# Let's check how the Detail/Edit Panel is wrapped.
# Currently: {showPanel ? ( <div...> ... </div> ) : ( <div...> empty state </div> )}
# This structure is fine and will automatically take 100% width since we removed the list.

with open('d:/ccf/frontend/src/app/evangelism/faro/groups/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Refactor complete")
