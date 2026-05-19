import sys

path = 'frontend/src/app/evangelism/events/page.tsx'
text = open(path, encoding='utf-8').read()
idx = text.rfind('}')

tail = """                                </select>
                            </div>
                        </div>
                        <div className="space-y-3 rounded-3xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                            <div className="flex items-center justify-between gap-3">
                                <div>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Plantillas de audiencia</p>
                                    <p className="text-sm font-bold text-slate-700 dark:text-slate-200">Aplica o guarda universos reutilizables</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button type="button" onClick={addSuggestedAudiencePresets} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-200 transition-all hover:bg-slate-100 dark:hover:bg-white/10">Sugerencias</button>
                                    <button type="button" onClick={() => saveAudiencePreset({ target_audience: editingEvent.target_audience || 'ALL', target_role_ids: editingEvent.target_role_ids || [], target_member_ids: editingEvent.target_member_ids || [] })} className="rounded-2xl bg-blue-600 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white transition-all hover:bg-blue-700">Guardar actual</button>
                                </div>
                            </div>
                            <div className="space-y-2">
                                {audiencePresets.length === 0 ? (
                                    <div className="rounded-2xl border border-dashed border-slate-200 dark:border-white/10 px-4 py-5 text-center text-sm text-slate-400">Aun no hay plantillas guardadas</div>
                                ) : audiencePresets.map((preset) => (
                                    <div key={preset.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-4 py-3">
                                        <div className="min-w-0">
                                            <p className="truncate text-sm font-bold text-slate-800 dark:text-white">{preset.name}</p>
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{preset.target_audience === 'ALL' ? 'Toda la iglesia' : preset.target_audience === 'ROLE' ? `${preset.target_role_ids.length} roles` : `${preset.target_member_ids.length} personas`}</p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button type="button" onClick={() => applyPresetToEditingEvent(preset.id)} className="rounded-2xl bg-slate-900 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-white transition-all hover:opacity-85 dark:bg-white/10">Aplicar</button>
                                            <button type="button" onClick={() => deleteAudiencePreset(preset.id)} className="rounded-2xl border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-500 transition-all hover:bg-slate-100 dark:hover:bg-white/5">Borrar</button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        {editingEvent.target_audience === 'MANUAL' && (
                            <div className="space-y-3">
                                <div className="flex items-center justify-between gap-3">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Personas esperadas</label>
                                    <span className="rounded-full bg-blue-50 dark:bg-blue-900/20 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-blue-600 dark:text-blue-300">{(editingEvent.target_member_ids || []).length} seleccionadas</span>
                                </div>
                                <input value={editManualSearch} onChange={e => setEditManualSearch(e.target.value)} placeholder="Buscar por nombre, correo o rol..." className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white" />
                                <div className="max-h-64 space-y-2 overflow-y-auto rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-3">
                                    {editManualMembers.map((member) => {
                                        const isSelected = (editingEvent.target_member_ids || []).includes(member.id);
                                        return (
                                            <button key={member.id} type="button" onClick={() => setEditingEvent({ ...editingEvent, target_member_ids: isSelected ? (editingEvent.target_member_ids || []).filter((value) => value !== member.id) : [...(editingEvent.target_member_ids || []), member.id], })} className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition-all ${isSelected ? 'border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20' : 'border-slate-200 bg-white dark:border-white/10 dark:bg-white/5'}`}>
                                                <div>
                                                    <p className="text-sm font-bold text-slate-800 dark:text-white">{member.first_name} {member.last_name}</p>
                                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{member.church_role || 'Sin rol'}</p>
                                                </div>
                                                <span className={`text-[10px] font-black uppercase tracking-widest ${isSelected ? 'text-blue-600 dark:text-blue-300' : 'text-slate-400'}`}>{isSelected ? 'Incluida' : 'Agregar'}</span>
                                            </button>
                                        );
                                    })}
                                    {editManualMembers.length === 0 && <div className="py-10 text-center text-sm text-slate-400">No hay personas para este filtro</div>}
                                </div>
                            </div>
                        )}
                        {editingEvent.status === 'CANCELLED' && (
                            <div className="animate-in fade-in slide-in-from-top-2 space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-widest text-red-400">Razón de Cancelación *</label>
                                <textarea value={editingEvent.cancellation_reason || ''} onChange={e => setEditingEvent({...editingEvent, cancellation_reason: e.target.value})} rows={3} placeholder="¿Por qué no se realizó este evento?" className="w-full px-4 py-3 rounded-2xl border border-red-200 dark:border-white/10 bg-red-50 dark:bg-black/20 focus:ring-2 focus:ring-red-500/20 outline-none font-bold text-sm text-red-900 dark:text-red-200 resize-none placeholder:text-red-300 dark:placeholder:text-red-700" />
                            </div>
                        )}
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Descripción</label>
                            <textarea value={editingEvent.description || ''} onChange={e => setEditingEvent({...editingEvent, description: e.target.value})} rows={3} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white resize-none" />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Ubicación</label>
                            <input type="text" value={editingEvent.location || ''} onChange={e => setEditingEvent({...editingEvent, location: e.target.value})} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white" />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Hora de Inicio</label>
                                <input type="time" value={editingEvent.start_time || ''} onChange={e => setEditingEvent({...editingEvent, start_time: e.target.value})} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white" />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Hora de Finalización</label>
                                <input type="time" value={editingEvent.end_time || ''} onChange={e => setEditingEvent({...editingEvent, end_time: e.target.value})} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white" />
                            </div>
                        </div>
                    </div>
                )}
            </WorkspaceDrawer>
        </EvangelismShell>
    );
}
"""

open(path, 'w', encoding='utf-8').write(text[:idx] + tail)
