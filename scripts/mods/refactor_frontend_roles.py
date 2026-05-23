import re

with open("frontend/src/app/crm/members/page.tsx", "r", encoding="utf-8") as f:
    c = f.read()

# 1. Remove hardcoded ROLES and ROLE_COLORS and getRoleColor
c = re.sub(r"const ROLES = \[.*?\];", "", c, flags=re.DOTALL)
c = re.sub(
    r"const ROLE_COLORS: Record<string, string> = \{.*?\};", "", c, flags=re.DOTALL
)
c = re.sub(r"function getRoleColor\(role: string\) \{.*?\}", "", c, flags=re.DOTALL)

# 2. Add dynamic states
state_addition = """
    const [roles, setRoles] = useState<any[]>([]);
    
    // Filters
"""
c = c.replace("    // Filters\n", state_addition)

# 3. Add API fetch for roles
api_addition = """
        const loadMembers = async () => {
            try {
                setLoading(true);
                const [membersData, rolesData] = await Promise.all([
                    apiFetch<any[]>('/crm/members', { token }).catch(() => []),
                    apiFetch<any[]>('/crm/roles', { token }).catch(() => [])
                ]);
                setMembers(membersData);
                setRoles(rolesData);
"""
c = re.sub(
    r"        const loadMembers = async \(\) => \{.*?setMembers\(data\);",
    api_addition,
    c,
    flags=re.DOTALL,
)

# 4. Modify getRoleColor usage
# In the return statement, it uses `getRoleColor(member.church_role || '')`
# We need a small helper inside the component
helper = """
    const getRoleColor = (roleName: string) => {
        const r = roles.find(x => roleName?.toLowerCase().includes(x.name.toLowerCase()));
        return r ? r.color : 'text-slate-600 bg-slate-100 dark:bg-white/10 dark:text-slate-400';
    };

    const stats = useMemo(() => {
"""
c = c.replace("    const stats = useMemo(() => {\n", helper)

# 5. Fix filter mapping
filter_mapping = """
                        <div className="flex items-center gap-2 overflow-x-auto pb-2 md:pb-0 scrollbar-none snap-x">
                            <button
                                onClick={() => setRoleFilter('Todos')}
                                className={clsx(
                                    "px-4 py-3 rounded-2xl text-[11px] font-black uppercase tracking-widest whitespace-nowrap transition-all shrink-0 snap-start",
                                    roleFilter === 'Todos' ? "bg-slate-800 text-white dark:bg-white dark:text-slate-900 shadow-md" : "bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10"
                                )}
                            >Todos</button>
                            {roles.map(role => (
                                <button
                                    key={role.id}
                                    onClick={() => setRoleFilter(role.name)}
                                    className={clsx(
                                        "px-4 py-3 rounded-2xl text-[11px] font-black uppercase tracking-widest whitespace-nowrap transition-all shrink-0 snap-start",
                                        roleFilter === role.name 
                                            ? "bg-slate-800 text-white dark:bg-white dark:text-slate-900 shadow-md"
                                            : "bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10"
                                    )}
                                >
                                    {role.name}
                                </button>
                            ))}
                        </div>
"""
c = re.sub(
    r'<div className="flex items-center gap-2 overflow-x-auto pb-2 md:pb-0 scrollbar-none snap-x">.*?</div>',
    filter_mapping,
    c,
    flags=re.DOTALL,
)

with open("frontend/src/app/crm/members/page.tsx", "w", encoding="utf-8") as f:
    f.write(c)

print("Dynamic roles injected into frontend!")
