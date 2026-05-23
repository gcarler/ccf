import codecs

with codecs.open("frontend/src/app/crm/events/[id]/page.tsx", "r", "utf-8") as f:
    c = f.read()

btn_old = """                            <button 
                                onClick={() => setActiveTab('session')}
                                className={clsx("px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all", activeTab === 'session' ? "bg-white dark:bg-[#252528] text-blue-600 shadow-sm" : "text-slate-500")}
                            >Configurar Sesion</button>
                        </div>"""

btn_new = """                            <button 
                                onClick={() => setActiveTab('session')}
                                className={clsx("px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all", activeTab === 'session' ? "bg-white dark:bg-[#252528] text-blue-600 shadow-sm" : "text-slate-500")}
                            >Configurar Sesion</button>
                            <button 
                                onClick={() => setActiveTab('analytics')}
                                className={clsx("px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all", activeTab === 'analytics' ? "bg-white dark:bg-[#252528] text-blue-600 shadow-sm" : "text-slate-500")}
                            >Analítica</button>
                        </div>"""

c = c.replace(btn_old, btn_new)

with codecs.open("frontend/src/app/crm/events/[id]/page.tsx", "w", "utf-8") as f:
    f.write(c)

print("Analitica tab button added")
