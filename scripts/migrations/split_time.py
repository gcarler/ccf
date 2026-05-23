import re

f = open("frontend/src/app/evangelism/events/page.tsx", encoding="utf-8").read()

# 1. State
f = f.replace(
    "fixed_date: '',\n        time: ''\n    });",
    "fixed_date: '',\n        start_time: '',\n        end_time: ''\n    });",
)
f = f.replace(
    "fixed_date: '', time: '' });", "fixed_date: '', start_time: '', end_time: '' });"
)

# 2. handleCreateEvent
f = f.replace(
    "time: newEvent.time,",
    "start_time: newEvent.start_time,\n            end_time: newEvent.end_time,",
)

# 3. Create Form JSX
old_create_time = """<div className="space-y-1.5">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Horario *</label>
                    <input
                        type="time"
                        required
                        value={newEvent.time}
                        onChange={e => setNewEvent({ ...newEvent, time: e.target.value })}
                        className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white"
                    />
                </div>"""

new_create_time = """<div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Hora de Inicio *</label>
                        <input
                            type="time"
                            required
                            value={newEvent.start_time}
                            onChange={e => setNewEvent({ ...newEvent, start_time: e.target.value })}
                            className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Hora de Finalización *</label>
                        <input
                            type="time"
                            required
                            value={newEvent.end_time}
                            onChange={e => setNewEvent({ ...newEvent, end_time: e.target.value })}
                            className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm text-slate-800 dark:text-white"
                        />
                    </div>
                </div>"""

f = f.replace(old_create_time, new_create_time)

# 4. Edit Form JSX
old_edit_time = """<div>
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 block">Horario</label>
                                <input type="time" value={editingEvent.time || ''} onChange={e => setEditingEvent({...editingEvent, time: e.target.value})} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-3 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                            </div>"""

new_edit_time = """<div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 block">Hora de Inicio</label>
                                    <input type="time" value={editingEvent.start_time || ''} onChange={e => setEditingEvent({...editingEvent, start_time: e.target.value})} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-3 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 block">Hora de Finalización</label>
                                    <input type="time" value={editingEvent.end_time || ''} onChange={e => setEditingEvent({...editingEvent, end_time: e.target.value})} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-3 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                                </div>
                            </div>"""

f = f.replace(old_edit_time, new_edit_time)

# 5. handleUpdateEvent
f = f.replace(
    "time: editingEvent.time",
    "start_time: editingEvent.start_time, end_time: editingEvent.end_time",
)

open("frontend/src/app/evangelism/events/page.tsx", "w", encoding="utf-8").write(f)
print("Updated frontend page.tsx successfully")
