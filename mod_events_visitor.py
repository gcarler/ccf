import codecs
import re

with codecs.open('frontend/src/app/crm/events/[id]/page.tsx', 'r', 'utf-8') as f:
    c = f.read()

# Add states for visitor form
states_old = """    const [sessionLoading, setSessionLoading] = useState(false);"""
states_new = """    const [sessionLoading, setSessionLoading] = useState(false);
    const [isVisitorModalOpen, setIsVisitorModalOpen] = useState(false);
    const [visitorForm, setVisitorForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });"""
c = c.replace(states_old, states_new)

# Add visitor submit function
func_old = """    const saveSession = async () => {"""
func_new = """    const handleAddVisitor = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token || !event) return;
        try {
            await apiFetch(`/crm/events/${event.id}/sessions/${sessionDate}/visitors`, {
                method: 'POST',
                token,
                body: visitorForm
            });
            toast.success("Visitante registrado con éxito");
            setIsVisitorModalOpen(false);
            setVisitorForm({ first_name: '', last_name: '', phone: '', email: '' });
            loadSessionData(sessionDate); // Reload the session to see the new attendance
        } catch {
            toast.error("Error al registrar visitante");
        }
    };

    const saveSession = async () => {"""
c = c.replace(func_old, func_new)

# Add Fast Check-in button to the UI
btn_old = """                                            <span className="text-xl font-black text-blue-600">{totalExpected > 0 ? Math.round((attendees.length / totalExpected) * 100) : 0}%</span>
                                        </div>
                                        <div className="w-full h-2 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
                                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${totalExpected > 0 ? Math.round((attendees.length / totalExpected) * 100) : 0}%` }} />
                                        </div>
                                    </div>"""

btn_new = """                                            <span className="text-xl font-black text-blue-600">{totalExpected > 0 ? Math.round((attendees.length / totalExpected) * 100) : 0}%</span>
                                        </div>
                                        <div className="w-full h-2 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden mb-6">
                                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${totalExpected > 0 ? Math.round((attendees.length / totalExpected) * 100) : 0}%` }} />
                                        </div>
                                        
                                        <button 
                                            onClick={() => setIsVisitorModalOpen(true)}
                                            className="w-full py-3 bg-violet-100 hover:bg-violet-200 dark:bg-violet-900/30 dark:hover:bg-violet-900/50 text-violet-700 dark:text-violet-300 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2 border border-violet-200 dark:border-violet-800"
                                        >
                                            <Plus size={16} /> Fast Check-In (Visitante)
                                        </button>
                                    </div>"""
c = c.replace(btn_old, btn_new)

# Add Dialog / Modal HTML at the end inside <CrmShell>
modal_html = """
        {/* Modal Visitante */}
        {isVisitorModalOpen && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
                <div className="bg-white dark:bg-[#1e1f21] w-full max-w-md rounded-[2rem] shadow-2xl p-6 relative animate-fade-in border border-slate-100 dark:border-white/5">
                    <button onClick={() => setIsVisitorModalOpen(false)} className="absolute top-6 right-6 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                    <h2 className="text-lg font-black text-slate-900 dark:text-white uppercase tracking-tight mb-6">Nuevo Visitante</h2>
                    <form onSubmit={handleAddVisitor} className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Nombre</label>
                                <input required value={visitorForm.first_name} onChange={e => setVisitorForm({...visitorForm, first_name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Juan" />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Apellido</label>
                                <input required value={visitorForm.last_name} onChange={e => setVisitorForm({...visitorForm, last_name: e.target.value})} className="w-full px-4 py-3 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Pérez" />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Teléfono (WhatsApp)</label>
                            <input value={visitorForm.phone} onChange={e => setVisitorForm({...visitorForm, phone: e.target.value})} className="w-full px-4 py-3 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="+57 300 000 0000" />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Correo Electrónico (Opcional)</label>
                            <input type="email" value={visitorForm.email} onChange={e => setVisitorForm({...visitorForm, email: e.target.value})} className="w-full px-4 py-3 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="correo@ejemplo.com" />
                        </div>
                        <div className="pt-4">
                            <button type="submit" className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/30 transition-all flex justify-center items-center gap-2">
                                <CheckCircle2 size={16} /> Guardar Asistencia
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        )}
"""

c = c.replace("        </CrmShell>", modal_html + "\n        </CrmShell>")

with codecs.open('frontend/src/app/crm/events/[id]/page.tsx', 'w', 'utf-8') as f:
    f.write(c)

print("Fast checkin modal added")
