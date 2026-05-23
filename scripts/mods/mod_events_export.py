import codecs
import re

with codecs.open("frontend/src/app/crm/events/[id]/page.tsx", "r", "utf-8") as f:
    c = f.read()

# Add download/export function
func_old = """    const handleAddVisitor = async (e: React.FormEvent) => {"""
func_new = """    const handleExportCsv = async () => {
        if (!token || !event) return;
        try {
            const res = await apiFetch<Blob>(`/crm/events/${event.id}/sessions/${sessionDate}/export`, {
                token,
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(res);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Reporte_${event.name}_${sessionDate}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } catch {
            toast.error("Error al exportar el reporte");
        }
    };

    const handleAddVisitor = async (e: React.FormEvent) => {"""
c = c.replace(func_old, func_new)

# Add Download button next to Save Agenda
ui_old = """                                    <button 
                                        onClick={saveSession}
                                        className="px-8 py-3 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/30 hover:scale-105 transition-all flex items-center gap-2"
                                    >
                                        <Save size={16}/> Guardar Agenda
                                    </button>"""
ui_new = """                                    <button 
                                        onClick={handleExportCsv}
                                        className="px-8 py-3 bg-emerald-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-emerald-500/30 hover:scale-105 transition-all flex items-center gap-2"
                                    >
                                        <Download size={16}/> Exportar Asistencia
                                    </button>
                                    <button 
                                        onClick={saveSession}
                                        className="px-8 py-3 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/30 hover:scale-105 transition-all flex items-center gap-2"
                                    >
                                        <Save size={16}/> Guardar Agenda
                                    </button>"""
c = c.replace(ui_old, ui_new)

with codecs.open("frontend/src/app/crm/events/[id]/page.tsx", "w", "utf-8") as f:
    f.write(c)

print("Export button added")
