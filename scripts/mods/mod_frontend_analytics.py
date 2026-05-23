import sys

with open("frontend/src/app/crm/events/[id]/page.tsx", "r", encoding="utf-8") as f:
    c = f.read()

# 1. State for Analytics
state_old = "    const [roles, setRoles] = useState<any[]>([]);"
state_new = """    const [roles, setRoles] = useState<any[]>([]);
    const [analytics, setAnalytics] = useState<any>(null);
    const [loadingAnalytics, setLoadingAnalytics] = useState(false);"""
c = c.replace(state_old, state_new)

# 2. Add Tab
tab_old = """                            <button 
                                onClick={() => setActiveTab('session')} 
                                className={`px-4 py-3 text-[11px] font-black uppercase tracking-widest whitespace-nowrap transition-all border-b-2 ${activeTab === 'session' ? 'border-blue-500 text-blue-600 dark:text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                            >
                                Sesión Actual
                            </button>
                        </div>"""

tab_new = """                            <button 
                                onClick={() => setActiveTab('session')} 
                                className={`px-4 py-3 text-[11px] font-black uppercase tracking-widest whitespace-nowrap transition-all border-b-2 ${activeTab === 'session' ? 'border-blue-500 text-blue-600 dark:text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                            >
                                Sesión Actual
                            </button>
                            <button 
                                onClick={() => { setActiveTab('analytics'); loadAnalytics(); }} 
                                className={`px-4 py-3 text-[11px] font-black uppercase tracking-widest whitespace-nowrap transition-all border-b-2 ${activeTab === 'analytics' ? 'border-blue-500 text-blue-600 dark:text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                            >
                                Analítica
                            </button>
                        </div>"""
c = c.replace(tab_old, tab_new)

# 3. Add loadAnalytics function before return
func_old = """    if (loading && !event) {"""
func_new = """    const loadAnalytics = async () => {
        if (!token || !event) return;
        setLoadingAnalytics(true);
        try {
            const data = await apiFetch<any>(`/crm/events/${event.id}/analytics`, { token });
            setAnalytics(data);
        } catch {
            addToast("Error al cargar analítica", "error");
        } finally {
            setLoadingAnalytics(false);
        }
    };

    if (loading && !event) {"""
c = c.replace(func_old, func_new)

# 4. Add the Analytics View inside the tabs
view_old = """                    {activeTab === 'session' && ("""
view_new = """                    {activeTab === 'analytics' && (
                        <div className="space-y-6">
                            {loadingAnalytics || !analytics ? (
                                <div className="text-center py-20 text-slate-400 font-medium">Cargando analítica...</div>
                            ) : (
                                <>
                                    {/* KPIs */}
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        <div className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl p-5 text-center">
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1">Promedio Histórico</p>
                                            <h3 className="text-3xl font-black text-slate-900 dark:text-white">{analytics.kpis.historical_avg}</h3>
                                            <p className="text-xs font-medium text-slate-500 mt-1">Personas por sesión</p>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl p-5 text-center">
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1">Tendencia de Crecimiento</p>
                                            <h3 className={`text-3xl font-black ${analytics.kpis.trend_percentage > 0 ? 'text-emerald-500' : analytics.kpis.trend_percentage < 0 ? 'text-red-500' : 'text-slate-500'}`}>
                                                {analytics.kpis.trend_percentage > 0 ? '+' : ''}{analytics.kpis.trend_percentage}%
                                            </h3>
                                            <p className="text-xs font-medium text-slate-500 mt-1">Respecto al mes anterior</p>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl p-5 text-center">
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1">Mes Pico (Récord)</p>
                                            <h3 className="text-3xl font-black text-blue-500">{analytics.kpis.peak_month.avg}</h3>
                                            <p className="text-xs font-black uppercase tracking-widest text-slate-500 mt-1">{analytics.kpis.peak_month.month}</p>
                                        </div>
                                    </div>
                                    
                                    {/* Gráfico de Barras CSS */}
                                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl p-6 shadow-sm">
                                        <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-8">Asistencia Promedio por Mes</h3>
                                        
                                        {analytics.monthly_data.length === 0 ? (
                                            <div className="text-center py-10 text-slate-400 text-sm">No hay datos suficientes para graficar.</div>
                                        ) : (
                                            <div className="flex items-end gap-2 h-64 mt-4 w-full overflow-x-auto pb-4 scrollbar-thin">
                                                {analytics.monthly_data.map((d: any) => {
                                                    // Calculate height percentage relative to peak month
                                                    const maxAvg = analytics.kpis.peak_month.avg || 1;
                                                    const heightPct = Math.max(5, Math.round((d.avg_attendance / maxAvg) * 100));
                                                    
                                                    return (
                                                        <div key={d.month} className="flex-1 min-w-[40px] max-w-[80px] flex flex-col items-center justify-end group">
                                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800 text-white text-[10px] font-bold px-2 py-1 rounded-md mb-2 whitespace-nowrap">
                                                                {d.avg_attendance} asis.
                                                            </div>
                                                            <div 
                                                                className="w-full bg-blue-100 dark:bg-blue-900/40 hover:bg-blue-500 dark:hover:bg-blue-500 rounded-t-lg transition-all duration-500" 
                                                                style={{ height: `${heightPct}%` }}
                                                            ></div>
                                                            <div className="mt-2 text-[9px] font-black uppercase tracking-widest text-slate-400 rotate-[-45deg] origin-top-left translate-y-2 translate-x-2">
                                                                {d.month}
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                    
                    {activeTab === 'session' && ("""
c = c.replace(view_old, view_new)

with open("frontend/src/app/crm/events/[id]/page.tsx", "w", encoding="utf-8") as f:
    f.write(c)
print("Updated event page!")
