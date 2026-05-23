import sys
import re

with open('frontend/src/app/crm/events/[id]/page.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

# Add absentees state and expected state
c = c.replace(
    "    const [attendees, setAttendees] = useState<any[]>([]);\n    const [metrics, setMetrics] = useState<Record<string, number>>({});",
    "    const [attendees, setAttendees] = useState<any[]>([]);\n    const [absentees, setAbsentees] = useState<any[]>([]);\n    const [metrics, setMetrics] = useState<Record<string, number>>({});\n    const [totalExpected, setTotalExpected] = useState<number>(0);\n    const [roles, setRoles] = useState<any[]>([]);"
)

# Modify loadSessionData
load_old = """                setAttendees(data.attendees || []);
                setMetrics(data.metrics || {});"""
load_new = """                setAttendees(data.attendees || []);
                setAbsentees(data.absentees || []);
                setTotalExpected(data.total_expected || 0);
                setMetrics(data.metrics || {});"""
c = c.replace(load_old, load_new)

# Modify loadEvent to fetch roles
evt_old = """                setEvent(data);
                
                // Initialize form"""
evt_new = """                setEvent(data);
                const rData = await apiFetch<any[]>('/crm/roles', { token }).catch(() => []);
                setRoles(rData);
                
                // Initialize form"""
c = c.replace(evt_old, evt_new)

# Add audience settings to form
# Look for Location field in the form
form_old = """                            <div>
                                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block">Ubicación</label>
                                <input value={editForm.location} onChange={e => setEditForm({...editForm, location: e.target.value})} className="w-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm outline-none font-medium" />
                            </div>"""

form_new = """                            <div>
                                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block">Ubicación</label>
                                <input value={editForm.location} onChange={e => setEditForm({...editForm, location: e.target.value})} className="w-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm outline-none font-medium" />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4 mt-4">
                            <div>
                                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block">Audiencia Esperada</label>
                                <select value={event.target_audience || 'ALL'} onChange={async (e) => {
                                    const val = e.target.value;
                                    await apiFetch(`/crm/events/${event.id}/audience`, {
                                        method: 'PUT', token, body: { target_audience: val, target_role_id: event.target_role_id }
                                    });
                                    loadEvent(); loadSessionData(sessionDate);
                                }} className="w-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm outline-none font-bold">
                                    <option value="ALL">Toda la Iglesia</option>
                                    <option value="ROLE">Un Ministerio/Rol Específico</option>
                                </select>
                            </div>
                            {event.target_audience === 'ROLE' && (
                                <div>
                                    <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block">Rol Específico</label>
                                    <select value={event.target_role_id || ''} onChange={async (e) => {
                                        const val = Number(e.target.value);
                                        await apiFetch(`/crm/events/${event.id}/audience`, {
                                            method: 'PUT', token, body: { target_audience: 'ROLE', target_role_id: val }
                                        });
                                        loadEvent(); loadSessionData(sessionDate);
                                    }} className="w-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-sm outline-none font-bold">
                                        <option value="" disabled>Selecciona un rol...</option>
                                        {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                                    </select>
                                </div>
                            )}"""

c = c.replace(form_old, form_new)

# Add the Absent list to the attendance panel
# Find:                                     <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-4">Métricas por Perfil</h3>
metrics_old = """                                    <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-4">Métricas por Perfil</h3>
                                    <div className="space-y-2">
                                        {Object.entries(metrics).map(([k, v]) => (
                                            <div key={k} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/5">
                                                <span className="text-xs font-bold text-slate-600 dark:text-slate-300 uppercase">{k}</span>
                                                <span className="text-sm font-black text-slate-900 dark:text-white">{v}</span>
                                            </div>
                                        ))}
                                    </div>"""

metrics_new = """                                    <div className="mb-8 p-6 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
                                        <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-4">Salud de Asistencia</h3>
                                        <div className="flex justify-between items-end mb-2">
                                            <span className="text-sm font-bold text-slate-600 dark:text-slate-300">Asistieron {attendees.length} de {totalExpected}</span>
                                            <span className="text-xl font-black text-blue-600">{totalExpected > 0 ? Math.round((attendees.length / totalExpected) * 100) : 0}%</span>
                                        </div>
                                        <div className="w-full h-2 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
                                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${totalExpected > 0 ? Math.round((attendees.length / totalExpected) * 100) : 0}%` }} />
                                        </div>
                                    </div>
                                    
                                    <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-4">Métricas por Perfil</h3>
                                    <div className="space-y-2 mb-8">
                                        {Object.entries(metrics).map(([k, v]) => (
                                            <div key={k} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/5">
                                                <span className="text-xs font-bold text-slate-600 dark:text-slate-300 uppercase">{k}</span>
                                                <span className="text-sm font-black text-slate-900 dark:text-white">{v}</span>
                                            </div>
                                        ))}
                                    </div>
                                    
                                    {absentees.length > 0 && (
                                        <>
                                            <h3 className="text-[11px] font-black uppercase tracking-widest text-red-400 mb-4">Faltaron a la sesión ({absentees.length})</h3>
                                            <div className="space-y-2 max-h-96 overflow-y-auto pr-2 scrollbar-thin">
                                                {absentees.map(a => (
                                                    <div key={a.member_id} className="p-3 bg-red-50/50 dark:bg-red-900/10 rounded-xl border border-red-100 dark:border-red-900/20 flex justify-between items-center group">
                                                        <div>
                                                            <p className="text-xs font-black uppercase text-slate-800 dark:text-slate-200">{a.name}</p>
                                                            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">{a.role}</p>
                                                        </div>
                                                        {a.phone && (
                                                            <a href={`https://wa.me/${a.phone.replace(/[^0-9]/g, '')}`} target="_blank" className="p-2 bg-emerald-100 text-emerald-600 rounded-lg opacity-0 group-hover:opacity-100 transition-all hover:scale-110">
                                                                <MessageCircle size={14} />
                                                            </a>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </>
                                    )}"""

# Need to import MessageCircle from lucide-react if not present
c = c.replace("Calendar, Users", "Calendar, Users, MessageCircle")
c = c.replace(metrics_old, metrics_new)

with open('frontend/src/app/crm/events/[id]/page.tsx', 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated Event Detail page!")
