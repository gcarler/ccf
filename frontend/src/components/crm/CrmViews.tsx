"use client";

import { AllCommunityModule,ColDef,ModuleRegistry,themeQuartz } from '@/lib/ag-grid-community-no-style';
import { AgGridReact } from 'ag-grid-react';
import { motion } from 'framer-motion';
import {
Calendar,
ChevronRight,
GraduationCap,
Heart,Mail,Phone,Star
} from 'lucide-react';
import { useEffect,useMemo,useRef,useState } from 'react';

ModuleRegistry.registerModules([AllCommunityModule]);

const _lightTheme = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 44, headerHeight: 36, backgroundColor: '#ffffff', foregroundColor: '#1e293b', borderColor: '#e2e8f0', oddRowBackgroundColor: '#f8fafc', headerBackgroundColor: '#f1f5f9', headerTextColor: '#475569', selectedRowBackgroundColor: '#eef2ff', accentColor: '#6366f1', cellHorizontalPaddingScale: 1 });
const _darkTheme  = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 44, headerHeight: 36, backgroundColor: 'rgb(15 23 42)', foregroundColor: '#e2e8f0', borderColor: 'rgba(255,255,255,0.08)', oddRowBackgroundColor: 'rgba(255,255,255,0.02)', headerBackgroundColor: 'rgba(255,255,255,0.04)', headerTextColor: '#94a3b8', selectedRowBackgroundColor: 'rgba(99,102,241,0.15)', accentColor: '#6366f1', cellHorizontalPaddingScale: 1 });

interface Persona {
    id: string;
    nombre_completo: string;
    email: string;
    phone: string;
    church_role: string;
    spiritual_status: string;
    spiritual_health: number;
    academy_progress: number;
    created_at: string;
}

interface CrmViewProps {
    personas: Persona[];
    onSelect?: (persona: Persona) => void;
}

// ----------------------------------------------------------------------
// 1. GRID VIEW (Classic Cards)
// ----------------------------------------------------------------------

export function CrmGridView({ personas, onSelect }: CrmViewProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {personas.map((persona, idx) => (
                <PersonaCard
                    key={persona.id}
                    persona={persona}
                    index={idx}
                    onClick={() => onSelect?.(persona)}
                />
            ))}
        </div>
    );
}

// Re-using the PersonaCard layout for Grid View
function PersonaCard({ persona, index, onClick }: { persona: Persona, index: number, onClick: () => void }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.02 }}
            onClick={onClick}
            className="group p-4 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 hover:border-blue-500/50 hover:shadow-2xl transition-all cursor-pointer relative overflow-hidden"
        >
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-4">
                    <div className="size-8 rounded-lg bg-gradient-to-br from-[hsl(var(--surface-2))] to-[hsl(var(--surface-2))] dark:from-white/10 dark:to-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:from-blue-600 group-hover:to-blue-700 group-hover:text-white transition-all shadow-sm">
                        <span className="text-base font-bold">{persona.nombre_completo?.charAt(0) ?? ''}</span>
                    </div>
                    <div>
                        <h4 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white leading-none mb-1 truncate max-w-[150px]">
                            {persona.nombre_completo}
                        </h4>
                        <span className="px-2 py-0.5 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            {persona.church_role || 'Persona'}
                        </span>
                    </div>
                </div>
                <div className="flex items-center gap-1 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                    <Heart size={12} className="text-[hsl(var(--primary))]" fill="currentColor" />
                    <span className="text-[10px] font-bold text-[hsl(var(--primary))]">{Math.round((persona.spiritual_health || 0.8) * 100)}%</span>
                </div>
            </div>

            <div className="space-y-3 mb-3">
                <div className="flex items-center gap-3 text-[hsl(var(--text-secondary))]">
                    <Mail size={14} />
                    <span className="text-xs font-bold truncate">{persona.email || 'Sin correo'}</span>
                </div>
                <div className="flex items-center gap-3 text-[hsl(var(--text-secondary))]">
                    <Phone size={14} />
                    <span className="text-xs font-bold">{persona.phone || 'Sin teléfono'}</span>
                </div>
            </div>

            <div className="pt-4 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                <div className="flex -space-x-2">
                    <div className="size-6 rounded-full bg-emerald-100 border-2 border-white dark:border-[#1e1f21] flex items-center justify-center text-emerald-600"><Star size={10} fill="currentColor" /></div>
                    <div className="size-6 rounded-full bg-blue-100 border-2 border-white dark:border-[#1e1f21] flex items-center justify-center text-[hsl(var(--primary))]"><GraduationCap size={10} /></div>
                </div>
                <span className="text-[9px] font-bold uppercase text-[hsl(var(--text-secondary))]">Ver Perfil <ChevronRight size={10} className="inline ml-1" /></span>
            </div>
        </motion.div>
    );
}


// ----------------------------------------------------------------------
// 2. TABLE / LIST VIEW
// ----------------------------------------------------------------------
interface TableProps extends CrmViewProps {
    isList?: boolean;
}

export function CrmTableView({ personas, onSelect, isList = false }: TableProps) {
    const gridRef = useRef<AgGridReact>(null);
    const [isDark, setIsDark] = useState(false);

    useEffect(() => {
        const check = () => setIsDark(document.documentElement.classList.contains('dark'));
        check();
        const obs = new MutationObserver(check);
        obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        return () => obs.disconnect();
    }, []);

    const colDefs = useMemo<ColDef[]>(() => {
        const cols: ColDef[] = [
            {
                headerName: 'Persona', flex: 2, minWidth: 180,
                cellRenderer: ({ data }: any) => {
                    const initials = data?.nombre_completo?.charAt(0) ?? '';
                    return (
                        <div className="flex items-center gap-3 h-full">
                            <div className="size-8 rounded-md bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-900/40 dark:to-blue-800/20 text-[hsl(var(--primary))] flex items-center justify-center font-bold text-sm flex-shrink-0">
                                {initials}
                            </div>
                            <div>
                                <div className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white leading-tight">{data?.nombre_completo}</div>
                                <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">ID: #{data?.id}</div>
                            </div>
                        </div>
                    );
                },
            },
            {
                headerName: 'Contacto', flex: 2, minWidth: 160,
                cellRenderer: ({ data }: any) => (
                    <div className="flex flex-col justify-center gap-0.5 h-full">
                        <div className="text-xs font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] flex items-center gap-1"><Mail size={11} /> {data?.email || '—'}</div>
                        <div className="text-xs text-[hsl(var(--text-secondary))] flex items-center gap-1"><Phone size={11} /> {data?.phone || '—'}</div>
                    </div>
                ),
            },
            {
                field: 'church_role', headerName: 'Rol', width: 140,
                cellRenderer: ({ value }: any) => {
                    const isLeader = String(value ?? '').toLowerCase().includes('líder') || String(value ?? '').toLowerCase().includes('lider');
                    return <span className={`px-2.5 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-wider ${isLeader ? 'bg-orange-100 text-orange-600 dark:bg-orange-900/30' : 'bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-900/30'}`}>{value || 'Persona'}</span>;
                },
            },
        ];

        if (!isList) {
            cols.splice(2, 0, {
                field: 'spiritual_status', headerName: 'Estado Espiritual', width: 160,
                cellRenderer: ({ value }: any) => (
                    <span className="px-2.5 py-0.5 bg-[hsl(var(--surface-2))] dark:bg-white/10 rounded-lg text-[10px] font-bold uppercase text-[hsl(var(--text-secondary))] tracking-wider">
                        {value || 'Nuevo'}
                    </span>
                ),
            });
            cols.push({
                headerName: 'Salud', width: 100,
                cellRenderer: ({ data }: any) => (
                    <div className="flex items-center gap-1 text-[hsl(var(--primary))] font-bold text-xs">
                        <Heart size={13} fill="currentColor" />
                        {Math.round((data?.spiritual_health || 0.8) * 100)}%
                    </div>
                ),
            });
        }

        return cols;
    }, [isList]);

    return (
        <div className="rounded-lg overflow-hidden border border-[hsl(var(--border))] dark:border-white/10 shadow-sm animate-fade-in">
            <AgGridReact
                ref={gridRef}
                theme={isDark ? _darkTheme : _lightTheme}
                rowData={personas}
                columnDefs={colDefs}
                defaultColDef={{ resizable: true, sortable: true, filter: true }}
                getRowId={(p) => String(p.data.id)}
                onRowClicked={(e) => onSelect?.(e.data)}
                rowStyle={{ cursor: 'pointer' }}
                suppressCellFocus
                domLayout="autoHeight"
            />
        </div>
    );
}

// ----------------------------------------------------------------------
// 3. KANBAN / BOARD VIEW
// ----------------------------------------------------------------------
export function CrmKanbanView({ personas, onSelect }: CrmViewProps) {
    const columns = useMemo(() => {
        const statuses = ['Nuevo', 'Consolidado', 'Activo', 'Líder', 'Inactivo'];
        const grouped = statuses.map(status => ({
            id: status,
            title: status,
            items: personas.filter(m => (m.spiritual_status || 'Nuevo') === status)
        }));

        // Add "Otros" for statuses not in the list
        const others = personas.filter(m => !statuses.includes(m.spiritual_status || 'Nuevo'));
        if (others.length > 0) {
            grouped.push({ id: 'Otros', title: 'Otros', items: others });
        }
        return grouped;
    }, [personas]);

    return (
        <div className="flex gap-4 overflow-x-auto pb-8 snap-x snap-mandatory animate-fade-in" style={{ minHeight: '60vh' }}>
            {columns.map(col => (
                <div key={col.id} className="w-[320px] shrink-0 snap-start flex flex-col bg-[hsl(var(--surface-1))]/50 dark:bg-black/10 rounded-md border border-[hsl(var(--border))]/50 dark:border-white/5 overflow-hidden">
                    <div className="p-4 border-b border-[hsl(var(--border))]/50 dark:border-white/5 flex items-center justify-between bg-[hsl(var(--surface-2))]/50 dark:bg-white/5">
                        <h3 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                            {col.title}
                        </h3>
                        <span className="px-2 py-0.5 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-xs font-bold text-[hsl(var(--text-secondary))]">
                            {col.items.length}
                        </span>
                    </div>

                    <div className="flex-1 p-3 space-y-3 overflow-y-auto">
                        {col.items.map(m => (
                            <div
                                key={m.id}
                                onClick={() => onSelect?.(m)}
                                className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg shadow-sm hover:shadow-md hover:border-blue-500/50 cursor-pointer transition-all group"
                            >
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-xs font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-colors">
                                        {m.nombre_completo?.charAt(0) ?? ''}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white truncate">
                                            {m.nombre_completo}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center justify-between mt-2">
                                    <span className="text-[10px] font-bold uppercase text-[hsl(var(--text-secondary))] tracking-wider">
                                        {m.church_role || 'Persona'}
                                    </span>
                                    <div className="flex gap-1 text-[10px] font-bold text-emerald-600">
                                        <Heart size={12} fill="currentColor" /> {Math.round((m.spiritual_health || 0.8) * 100)}%
                                    </div>
                                </div>
                            </div>
                        ))}
                        {col.items.length === 0 && (
                            <div className="h-24 flex items-center justify-center border-2 border-dashed border-[hsl(var(--border))] dark:border-white/5 rounded-lg text-xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                Vacío
                            </div>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
}

// ----------------------------------------------------------------------
// 4. CALENDAR VIEW
// ----------------------------------------------------------------------
export function CrmCalendarView({ personas, onSelect }: CrmViewProps) {
    // Generar un calendario mensual estático para la demo
    const days = Array.from({ length: 35 }, (_, i) => i + 1);

    return (
        <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-md overflow-hidden animate-fade-in shadow-sm">
            <div className="p-4 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                <h3 className="text-sm font-bold tracking-tight"><Calendar size={20} className="inline mr-2 text-[hsl(var(--text-secondary))]" /> Calendario de Registros</h3>
            </div>
            <div className="grid grid-cols-7 gap-px bg-[hsl(var(--surface-3))] dark:bg-white/10">
                {['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'].map(d => (
                    <div key={d} className="bg-[hsl(var(--surface-1))] dark:bg-[#1a1c1e] p-3 text-center text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        {d}
                    </div>
                ))}
            </div>
            <div className="grid grid-cols-7 gap-px bg-[hsl(var(--surface-3))] dark:bg-white/10">
                {days.map(d => {
                    const dayPersonas = personas.filter(m => {
                        const date = new Date(m.created_at);
                        return date.getDate() === (d > 31 ? d - 31 : d);
                    });

                    return (
                        <div key={d} className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] min-h-12 p-2 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">
                            <span className="text-xs font-bold text-[hsl(var(--text-secondary))] mb-2 block">{d > 31 ? d - 31 : d}</span>
                            <div className="space-y-1">
                                {dayPersonas.map(m => (
                                    <div
                                        key={m.id}
                                        onClick={() => onSelect?.(m)}
                                        className="text-[10px] font-bold px-2 py-1 bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-900/30 rounded truncate cursor-pointer hover:bg-blue-100"
                                    >
                                        {m.nombre_completo}
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// 5. GANTT VIEW
// ----------------------------------------------------------------------
export function CrmGanttView({ personas }: CrmViewProps) {
    // Un timeline hiper simple de registros
    const sorted = [...personas].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()).slice(0, 15);

    return (
        <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] shadow-sm rounded-md border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden animate-fade-in py-1.5 px-3">
            <h3 className="text-sm font-bold tracking-tight mb-3">Timeline de Integración (Últimos 15)</h3>
            <div className="space-y-3 relative before:absolute before:inset-0 before:ml-[11px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent via-[hsl(var(--surface-2))] dark:before:via-white/5 before:to-transparent">
                {sorted.map(m => (
                    <div key={m.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-6 h-6 rounded-full border-4 border-white dark:border-[#1e1f21] bg-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2"></div>
                        <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 shadow-sm">
                            <div className="flex items-center justify-between mb-1">
                                <div className="font-bold text-sm text-[hsl(var(--text-primary))] dark:text-white">{m.nombre_completo}</div>
                                <time className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase">{new Date(m.created_at).toLocaleDateString()}</time>
                            </div>
                            <div className="text-xs text-[hsl(var(--text-secondary))] font-bold">{m.church_role || 'Persona'} ({m.spiritual_status || 'Nuevo'})</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

// Ensure PersonaCard inside CRMClient.tsx is either removed or we keep it.
// I'll export everything.
