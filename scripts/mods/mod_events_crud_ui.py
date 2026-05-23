f = open("frontend/src/app/crm/events/page.tsx", encoding="utf-8")
c = f.read()
f.close()

# 1. Add Edit/Pencil import
c = c.replace(
    "import {\n    Calendar,\n    Plus,\n    QrCode,\n    List,\n    LayoutGrid,\n    ArrowRight,\n    Download,\n    Scan,\n    Users,\n    Search,\n    ChevronRight\n} from 'lucide-react';",
    "import {\n    Calendar,\n    Plus,\n    QrCode,\n    List,\n    LayoutGrid,\n    ArrowRight,\n    Download,\n    Scan,\n    Users,\n    Search,\n    ChevronRight,\n    Pencil,\n    Trash2,\n    MoreVertical\n} from 'lucide-react';",
)

# 2. Add edit/delete state
c = c.replace(
    "    const [roles, setRoles] = useState<any[]>([]);",
    "    const [roles, setRoles] = useState<any[]>([]);\n    const [editingEvent, setEditingEvent] = useState<any>(null);\n    const [deletingEventId, setDeletingEventId] = useState<number | null>(null);\n    const [menuOpenId, setMenuOpenId] = useState<number | null>(null);",
)

# 3. Add edit/delete handlers before the return statement
handler_old = "    return (\n        <CrmShell"
handler_new = """    const handleDeleteEvent = async (evId: number) => {
        if (!token) return;
        try {
            await apiFetch(`/crm/events/${evId}`, { method: 'DELETE', token });
            setEvents(prev => prev.filter(e => e.id !== evId));
            toast.success('Evento eliminado correctamente');
        } catch {
            toast.error('Error al eliminar el evento');
        } finally {
            setDeletingEventId(null);
        }
    };

    const handleUpdateEvent = async (evId: number, payload: any) => {
        if (!token) return;
        try {
            await apiFetch(`/crm/events/${evId}`, { method: 'PUT', body: payload, token });
            setEvents(prev => prev.map(e => e.id === evId ? { ...e, ...payload } : e));
            toast.success('Evento actualizado');
            setEditingEvent(null);
        } catch {
            toast.error('Error al actualizar el evento');
        }
    };

    return (
        <CrmShell"""

c = c.replace(handler_old, handler_new)

# 4. Add three-dot menu to the card footer
card_footer_old = '                            <div className="mt-6 flex items-center justify-between">\n                                <button onClick={(e) => { e.stopPropagation(); openQr(ev); }} className="size-11 flex items-center justify-center bg-slate-50 dark:bg-white/5 hover:bg-violet-600 text-slate-400 hover:text-white rounded-xl transition-all mr-2 shrink-0" title="Generar QR">\n                                    <QrCode size={18} />\n                                </button>\n                                <button onClick={(e) => { e.stopPropagation(); openAttendance(ev); }} className="flex-1 py-3 bg-slate-50 dark:bg-white/5 group-hover:bg-blue-600 text-slate-500 group-hover:text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">\n                                    Panel de Asistencia\n                                </button>\n                                <ArrowRight size={16} className="ml-3 text-slate-300 group-hover:text-blue-500 transition-all opacity-0 group-hover:opacity-100" />\n                            </div>'

card_footer_new = """                            <div className="mt-6 flex items-center justify-between gap-2">
                                <button onClick={(e) => { e.stopPropagation(); openQr(ev); }} className="size-10 flex items-center justify-center bg-slate-50 dark:bg-white/5 hover:bg-violet-600 text-slate-400 hover:text-white rounded-xl transition-all shrink-0" title="Generar QR">
                                    <QrCode size={16} />
                                </button>
                                <button onClick={(e) => { e.stopPropagation(); openAttendance(ev); }} className="flex-1 py-3 bg-slate-50 dark:bg-white/5 group-hover:bg-blue-600 text-slate-500 group-hover:text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
                                    Panel de Asistencia
                                </button>
                                <div className="relative shrink-0" onClick={e => e.stopPropagation()}>
                                    <button
                                        onClick={() => setMenuOpenId(menuOpenId === ev.id ? null : ev.id)}
                                        className="size-10 flex items-center justify-center bg-slate-50 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-400 rounded-xl transition-all"
                                    >
                                        <MoreVertical size={16} />
                                    </button>
                                    {menuOpenId === ev.id && (
                                        <div className="absolute right-0 bottom-12 z-50 bg-white dark:bg-[#18181b] border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl overflow-hidden w-40 animate-in fade-in slide-in-from-bottom-2">
                                            <button
                                                onClick={() => { setEditingEvent(ev); setMenuOpenId(null); }}
                                                className="w-full flex items-center gap-3 px-4 py-3 text-sm font-bold text-slate-700 dark:text-white hover:bg-blue-50 dark:hover:bg-white/5 transition-all"
                                            >
                                                <Pencil size={14} className="text-blue-500" /> Editar
                                            </button>
                                            <button
                                                onClick={() => { setDeletingEventId(ev.id); setMenuOpenId(null); }}
                                                className="w-full flex items-center gap-3 px-4 py-3 text-sm font-bold text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10 transition-all"
                                            >
                                                <Trash2 size={14} /> Eliminar
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>"""

c = c.replace(card_footer_old, card_footer_new)

# 5. Add confirm delete modal + edit modal at end before closing tag of component
modal_old = "    );\n}"
modal_new = """            {/* DELETE CONFIRM MODAL */}
            {deletingEventId && (
                <div className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setDeletingEventId(null)}>
                    <div className="bg-white dark:bg-[#1e1f21] rounded-[2rem] p-8 max-w-sm w-full shadow-2xl border border-slate-200 dark:border-white/10" onClick={e => e.stopPropagation()}>
                        <div className="size-14 bg-red-500/10 text-red-500 rounded-2xl flex items-center justify-center mx-auto mb-5">
                            <Trash2 size={24} />
                        </div>
                        <h3 className="text-lg font-black text-center text-slate-900 dark:text-white mb-2">¿Eliminar Evento?</h3>
                        <p className="text-sm text-slate-500 text-center mb-6">Esta acción eliminará todo el historial de asistencia del evento. Es irreversible.</p>
                        <div className="flex gap-3">
                            <button onClick={() => setDeletingEventId(null)} className="flex-1 py-3 bg-slate-100 dark:bg-white/5 text-slate-700 dark:text-white rounded-2xl text-sm font-bold hover:bg-slate-200 transition-all">Cancelar</button>
                            <button onClick={() => handleDeleteEvent(deletingEventId)} className="flex-1 py-3 bg-red-600 hover:bg-red-700 text-white rounded-2xl text-sm font-bold transition-all">Sí, Eliminar</button>
                        </div>
                    </div>
                </div>
            )}

            {/* EDIT MODAL */}
            {editingEvent && (
                <div className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setEditingEvent(null)}>
                    <div className="bg-white dark:bg-[#1e1f21] rounded-[2rem] p-8 max-w-md w-full shadow-2xl border border-slate-200 dark:border-white/10" onClick={e => e.stopPropagation()}>
                        <h3 className="text-lg font-black text-slate-900 dark:text-white mb-6 flex items-center gap-2"><Pencil size={18} className="text-blue-500" /> Editar Evento</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 block">Nombre</label>
                                <input type="text" value={editingEvent.name} onChange={e => setEditingEvent({...editingEvent, name: e.target.value})} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-3 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                            </div>
                            <div>
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 block">Descripción</label>
                                <textarea value={editingEvent.description || ''} onChange={e => setEditingEvent({...editingEvent, description: e.target.value})} rows={3} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-3 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
                            </div>
                            <div>
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 block">Ubicación</label>
                                <input type="text" value={editingEvent.location || ''} onChange={e => setEditingEvent({...editingEvent, location: e.target.value})} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-3 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                            </div>
                        </div>
                        <div className="flex gap-3 mt-6">
                            <button onClick={() => setEditingEvent(null)} className="flex-1 py-3 bg-slate-100 dark:bg-white/5 text-slate-700 dark:text-white rounded-2xl text-sm font-bold hover:bg-slate-200 transition-all">Cancelar</button>
                            <button onClick={() => handleUpdateEvent(editingEvent.id, { name: editingEvent.name, description: editingEvent.description, location: editingEvent.location })} className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl text-sm font-bold transition-all flex items-center justify-center gap-2"><Pencil size={14} /> Guardar Cambios</button>
                        </div>
                    </div>
                </div>
            )}
        </CrmShell>
    );
}"""

c = c.replace("        </CrmShell>\n    );\n}", modal_new)

open("frontend/src/app/crm/events/page.tsx", "w", encoding="utf-8").write(c)
print("Frontend fixes applied: menu 3-dots + edit modal + delete confirm")
