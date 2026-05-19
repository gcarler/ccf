import sys

with open('frontend/src/app/crm/events/page.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. State
state_old = "    const [members, setMembers] = useState<Member[]>([]);"
state_new = "    const [members, setMembers] = useState<Member[]>([]);\n    const [stats, setStats] = useState<any[]>([]);"
c = c.replace(state_old, state_new)

# 2. fetchData
fetch_real_old = """    const fetchData = async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [eventsRes, membersRes] = await Promise.all([
                apiFetch<Event[]>('/crm/events/', { token, cache: 'no-store' }),
                apiFetch<Member[]>('/crm/members/', { token, cache: 'no-store' })
            ]);"""
fetch_real_new = """    const fetchData = async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [eventsRes, membersRes, statsRes] = await Promise.all([
                apiFetch<Event[]>('/crm/events/', { token, cache: 'no-store' }),
                apiFetch<Member[]>('/crm/members/', { token, cache: 'no-store' }),
                apiFetch<any[]>('/crm/events/dashboard-stats', { token, cache: 'no-store' })
            ]);"""
c = c.replace(fetch_real_old, fetch_real_new)
    
set_old = """            setEvents(Array.isArray(eventsRes) ? eventsRes : []);
            setMembers(Array.isArray(membersRes) ? membersRes : []);"""
set_new = """            setEvents(Array.isArray(eventsRes) ? eventsRes : []);
            setMembers(Array.isArray(membersRes) ? membersRes : []);
            setStats(Array.isArray(statsRes) ? statsRes : []);"""
c = c.replace(set_old, set_new)

# 3. Add to the Grid View
grid_card_old = """                                    <div className="flex items-center gap-2">
                                        <div className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest ${EVENT_TYPE_COLOR[event.event_type] || 'bg-slate-100 text-slate-500'}`}>
                                            {EVENT_TYPE_LABEL[event.event_type] || 'Evento'}
                                        </div>
                                    </div>"""
grid_card_new = """                                    <div className="flex items-center gap-2">
                                        <div className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest ${EVENT_TYPE_COLOR[event.event_type] || 'bg-slate-100 text-slate-500'}`}>
                                            {EVENT_TYPE_LABEL[event.event_type] || 'Evento'}
                                        </div>
                                    </div>
                                    {(() => {
                                        const evStat = stats.find(s => s.event_id === event.id);
                                        if (evStat && evStat.expected > 0) {
                                            return (
                                                <div className="mt-4 pt-4 border-t border-slate-100 dark:border-white/5">
                                                    <div className="flex justify-between items-center mb-1">
                                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Asistencia Última Sesión</span>
                                                        <span className="text-[10px] font-black text-blue-600">{evStat.rate}%</span>
                                                    </div>
                                                    <div className="w-full bg-slate-100 dark:bg-white/5 h-1.5 rounded-full overflow-hidden">
                                                        <div className="bg-blue-500 h-full rounded-full" style={{ width: `${evStat.rate}%` }} />
                                                    </div>
                                                    <p className="text-[9px] text-slate-400 mt-1">{evStat.attended} / {evStat.expected} personas</p>
                                                </div>
                                            );
                                        }
                                        return null;
                                    })()}"""
c = c.replace(grid_card_old, grid_card_new)

with open('frontend/src/app/crm/events/page.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
print("Updated Dashboard!")
