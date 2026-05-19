f = open('frontend/src/app/crm/events/[id]/page.tsx', encoding='utf-8')
c = f.read()
f.close()

# Add total_absentees banner right after the metrics section
# Insert after the "Desglose por Ministerio" block inside the attendance panel
old = """                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </main>

        {/* Modal Visitante */}"""

new = """                                            </div>

                                            {/* Absentees Banner */}
                                            {(sessionData?.total_absentees ?? 0) > 0 && (
                                                <div className="mt-6 p-4 rounded-2xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-500/20 flex items-center justify-between gap-4">
                                                    <div>
                                                        <p className="text-xs font-black uppercase tracking-widest text-amber-700 dark:text-amber-400">Inasistentes</p>
                                                        <p className="text-2xl font-black text-amber-700 dark:text-amber-400 mt-0.5">{sessionData?.total_absentees}</p>
                                                        {sessionData?.absentees_truncated && (
                                                            <p className="text-[10px] text-amber-600/70 mt-1">Mostrando {sessionData?.absentees?.length} de {sessionData?.total_absentees}. Descarga el CSV para ver todos.</p>
                                                        )}
                                                    </div>
                                                    <button
                                                        onClick={handleExportCsv}
                                                        className="shrink-0 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-2"
                                                    >
                                                        <Download size={12} /> Exportar Lista
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </main>

        {/* Modal Visitante */}"""

if old in c:
    c = c.replace(old, new)
    # Make sure Download is imported
    if 'Download' not in c:
        c = c.replace("import {", "import { Download,\n")
    open('frontend/src/app/crm/events/[id]/page.tsx', 'w', encoding='utf-8').write(c)
    print("Absentees banner added to session page")
else:
    print("Target block not found - might have different whitespace")
    # Try finding and adding it differently
    idx = c.find('{/* Modal Visitante */}')
    if idx > 0:
        # Find the closest </main> before it
        main_idx = c.rfind('</main>', 0, idx)
        if main_idx > 0:
            insert_point = c.rfind('</div>', 0, main_idx) 
            # Let's just try to inject the banner near the metrics section
            metrics_pattern = "{sessionData?.metrics && Object.entries(sessionData.metrics).map(([key, val]) => ("
            if metrics_pattern in c:
                # Find the closing div after this metrics block
                metrics_idx = c.find(metrics_pattern)
                close_idx = c.find("</div>", metrics_idx + 500)
                close_idx2 = c.find("</div>", close_idx + 1)  # closing the space-y-4
                close_idx3 = c.find("</div>", close_idx2 + 1)  # closing the block
                
                banner = """

                                            {/* Absentees Banner */}
                                            {(sessionData?.total_absentees ?? 0) > 0 && (
                                                <div className="mt-6 p-4 rounded-2xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-500/20 flex items-center justify-between gap-4">
                                                    <div>
                                                        <p className="text-xs font-black uppercase tracking-widest text-amber-700 dark:text-amber-400">Inasistentes</p>
                                                        <p className="text-2xl font-black text-amber-700 dark:text-amber-400 mt-0.5">{sessionData?.total_absentees}</p>
                                                        {sessionData?.absentees_truncated && (
                                                            <p className="text-[10px] text-amber-600/70 mt-1">Descarga el CSV para ver la lista completa.</p>
                                                        )}
                                                    </div>
                                                    <button onClick={handleExportCsv} className="shrink-0 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">Exportar</button>
                                                </div>
                                            )}"""
                c = c[:close_idx3] + banner + c[close_idx3:]
                open('frontend/src/app/crm/events/[id]/page.tsx', 'w', encoding='utf-8').write(c)
                print("Absentees banner injected via position search")
