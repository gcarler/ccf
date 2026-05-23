import codecs

with codecs.open("frontend/src/app/crm/events/page.tsx", "r", "utf-8") as f:
    c = f.read()

# 1. State update
state_old = """    const [newEvent, setNewEvent] = useState({
        name: '',
        description: '',
        event_type: 'PERMANENT',
        day_of_week: '0',
        month_day: '',
        fixed_date: ''
    });"""

state_new = """    const [newEvent, setNewEvent] = useState({
        name: '',
        description: '',
        event_type: 'PERMANENT',
        target_audience: 'ALL',
        target_role_id: '',
        day_of_week: '0',
        month_day: '',
        fixed_date: ''
    });
    
    const [roles, setRoles] = useState<any[]>([]);
    
    useEffect(() => {
        if (token) {
            apiFetch<any[]>('/crm/roles', { token }).then(setRoles).catch(() => {});
        }
    }, [token]);"""

c = c.replace(state_old, state_new)

# 2. handleCreateEvent payload
payload_old = """        const payload: any = {
            name: newEvent.name,
            description: newEvent.description,
            event_type: newEvent.event_type,
        };"""

payload_new = """        const payload: any = {
            name: newEvent.name,
            description: newEvent.description,
            event_type: newEvent.event_type,
            target_audience: newEvent.target_audience,
            target_role_id: newEvent.target_audience === 'ROLE' ? Number(newEvent.target_role_id) : null
        };"""

c = c.replace(payload_old, payload_new)

# 3. handleCreateEvent reset
reset_old = """setNewEvent({ name: '', description: '', event_type: 'PERMANENT', day_of_week: '0', month_day: '', fixed_date: '' });"""
reset_new = """setNewEvent({ name: '', description: '', event_type: 'PERMANENT', target_audience: 'ALL', target_role_id: '', day_of_week: '0', month_day: '', fixed_date: '' });"""
c = c.replace(reset_old, reset_new)

# 4. Add fields to the drawer form
form_old = """                <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Tipo de Evento *</label>
                    <select
                        required
                        value={newEvent.event_type}
                        onChange={e => setNewEvent({ ...newEvent, event_type: e.target.value })}
                        className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white appearance-none"
                    >
                        <option value="PERMANENT">📅 Semanal / Rutinario</option>
                        <option value="MONTHLY">🗓️ Mensual</option>
                        <option value="ANNUAL">🎉 Anual</option>
                        <option value="ONCE">📌 Única Vez / Fecha Fija</option>
                        <option value="SPECIAL">⭐ Especial / Campaña</option>
                        <option value="FARO">🏠 Faro en Casa / Célula</option>
                        <option value="ONLINE">💻 En Línea / Transmisión</option>
                    </select>
                </div>"""

form_new = (
    form_old
    + """

                <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Audiencia Objetivo</label>
                    <select
                        value={newEvent.target_audience}
                        onChange={e => setNewEvent({ ...newEvent, target_audience: e.target.value })}
                        className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white appearance-none"
                    >
                        <option value="ALL">Toda la Iglesia</option>
                        <option value="ROLE">Un Ministerio/Rol Específico</option>
                    </select>
                </div>

                {newEvent.target_audience === 'ROLE' && (
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Rol Específico *</label>
                        <select
                            required
                            value={newEvent.target_role_id}
                            onChange={e => setNewEvent({ ...newEvent, target_role_id: e.target.value })}
                            className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white appearance-none"
                        >
                            <option value="" disabled>Selecciona un rol...</option>
                            {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                        </select>
                    </div>
                )}"""
)

c = c.replace(form_old, form_new)

with codecs.open("frontend/src/app/crm/events/page.tsx", "w", "utf-8") as f:
    f.write(c)

print("Phase 1 completed: Event Creation Drawer updated.")
