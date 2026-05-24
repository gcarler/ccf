"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    Sparkles,
    Zap,
    Palette,
    Settings,
    Smartphone,
    Bot,
    GanttChart,
    Heart,
    KanbanSquare,
    Shield,
    Save,
    RotateCcw
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import clsx from 'clsx';

const FEATURE_CARDS = [
    { id: 'gantt', label: 'Vista de Gantt', desc: 'Habilita el cronograma interactivo en proyectos.', icon: GanttChart, color: 'text-blue-500' },
    { id: 'ai_coach', label: 'Optimus Brain Coach', desc: 'Asistente de IA para academia y CRM.', icon: Bot, color: 'text-sky-500' },
    { id: 'call_center', label: 'Call Center Pastoral', icon: Smartphone, desc: 'Gestión de llamadas y mensajes masivos.', color: 'text-amber-500' },
    { id: 'prayer_wall', label: 'Muro de Intercesión', icon: Heart, desc: 'Registro público de peticiones de oración.', color: 'text-rose-500' },
    { id: 'kanban', label: 'Tableros Kanban', icon: KanbanSquare, desc: 'Visualización de procesos por arrastre.', color: 'text-emerald-500' },
    { id: 'audit_logs', label: 'Auditoría de Staff', icon: Shield, desc: 'Registro detallado de acciones administrativas.', color: 'text-indigo-500' },
];
const EXPERIENCE_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function WorkspaceExperienceManager() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [config, setConfig] = useState<any>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        const fetchConfig = async () => {
            if (!token) return;
            try {
                const data = await apiFetch('/workspace/config', { token });
                setConfig(data);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchConfig();
    }, [token]);

    const toggleFeature = (id: string) => {
        setConfig((prev: any) => ({
            ...prev,
            features_enabled: {
                ...prev.features_enabled,
                [id]: !prev.features_enabled[id]
            }
        }));
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await apiFetch('/workspace/config', {
                method: 'PATCH',
                token,
                body: config
            });
            addToast("Configuración del Workspace actualizada", "success");
        } catch (err) {
            addToast("Error al guardar configuración", "error");
        } finally {
            setIsSaving(false);
        }
    };

    if (loading) return <div className="p-4 text-center text-slate-500 font-semibold uppercase tracking-wide animate-pulse">Cargando Brain...</div>;

    const featureRows = FEATURE_CARDS.map((feature, index) => ({
        ...feature,
        enabled: !!config?.features_enabled?.[feature.id],
        date: new Date(Date.now() + index * 86400000).toISOString(),
    }));

    const groupedFeatures = [
        { id: 'enabled', label: 'Activas', rows: featureRows.filter(feature => feature.enabled) },
        { id: 'disabled', label: 'Inactivas', rows: featureRows.filter(feature => !feature.enabled) },
    ];

    const calendarEvents = featureRows.map((feature) => ({
        id: feature.id,
        title: feature.label,
        date: feature.date.split('T')[0],
        color: feature.enabled ? 'emerald' as const : 'amber' as const,
        location: feature.enabled ? 'Activo' : 'Inactivo',
    }));

    const ganttItems = featureRows.map((feature) => ({
        id: feature.id,
        title: feature.label,
        subtitle: feature.desc,
        start_date: feature.date,
        end_date: feature.date,
        color: feature.enabled ? 'emerald' as const : 'amber' as const,
        progress: feature.enabled ? 100 : 35,
    }));

    const renderList = () => (
        <div className="space-y-4">
            {featureRows.map((feature) => (
                <button key={feature.id} onClick={() => toggleFeature(feature.id)} className="w-full text-left bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg p-3 flex items-center justify-between gap-3 hover:border-blue-300 transition-all">
                    <div className="flex items-center gap-3">
                        <div className={clsx("size-7 rounded-lg flex items-center justify-center", feature.enabled ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-400")}>
                            <feature.icon size={24} />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{feature.label}</h3>
                            <p className="mt-1 text-[10px] font-bold text-slate-400 uppercase tracking-wide">{feature.desc}</p>
                        </div>
                    </div>
                    <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", feature.enabled ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-500")}>{feature.enabled ? 'Activo' : 'Inactivo'}</span>
                </button>
            ))}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
            <table className="w-full text-left">
                <thead className="bg-slate-50 dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Feature</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden md:table-cell">Descripción</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Estado</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                    {featureRows.map((feature) => (
                        <tr key={feature.id} onClick={() => toggleFeature(feature.id)} className="hover:bg-slate-50 dark:hover:bg-white/[0.03] cursor-pointer">
                            <td className="px-3 py-1.5 text-sm font-bold text-slate-800 dark:text-slate-100">{feature.label}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-[11px] text-slate-500">{feature.desc}</td>
                            <td className="px-3 py-1.5"><span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", feature.enabled ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-500")}>{feature.enabled ? 'Activo' : 'Inactivo'}</span></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {groupedFeatures.map((group) => (
                <section key={group.id} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{group.label}</span>
                        <span className="font-semibold text-slate-400">{group.rows.length}</span>
                    </div>
                    <div className="space-y-3">
                        {group.rows.map((feature) => (
                            <button key={feature.id} onClick={() => toggleFeature(feature.id)} className="w-full text-left bg-white dark:bg-white/[0.05] border border-slate-100 dark:border-white/5 rounded-lg p-4 hover:border-blue-300 transition-all">
                                <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{feature.label}</p>
                                <p className="mt-2 text-[10px] font-bold text-slate-400">{feature.desc}</p>
                            </button>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Ajustes', icon: Settings }, { label: 'Experiencia de Usuario', icon: Sparkles }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={EXPERIENCE_VIEWS}
                rightActions={
                    <div className="flex items-center gap-2">
                        <button onClick={() => router.back()} className="px-4 py-2 font-semibold text-slate-500 uppercase tracking-wide hover:text-slate-800">Cancelar</button>
                        <button 
                            onClick={handleSave} disabled={isSaving}
                            className="flex items-center gap-2 px-3 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl active:scale-95 transition-all"
                        >
                            {isSaving ? <RotateCcw className="animate-spin" size={14} /> : <Save size={14} />} Guardar Workspace
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-3 lg:p-4 relative pb-4">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />

 <div className="w-full space-y-3 relative z-10">
                    
                    {/* Header */}
                    <header className="space-y-4">
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-sky-50 dark:bg-sky-900/20 text-sky-600 rounded-lg text-[10px] font-semibold uppercase tracking-wide border border-sky-100 dark:border-sky-900/30">
                            <Zap size={14} /> Workspace Experience Manager v3.0
                        </div>
                        <h1 className="text-lg lg:text-xl font-bold text-slate-800 dark:text-white tracking-tighter leading-none">
                            El cerebro de tu <span className="text-blue-600 italic">interfaz.</span>
                        </h1>
                        <p className="text-xl text-slate-500 dark:text-slate-400 font-medium max-w-2xl leading-relaxed">
                            Activa funcionalidades de alto nivel, personaliza el motor visual y define el flujo de herramientas para todo tu equipo.
                        </p>
                    </header>

                    {viewType === 'list' ? (
                        renderList()
                    ) : viewType === 'table' ? (
                        renderTable()
                    ) : viewType === 'board' || viewType === 'kanban' ? (
                        renderBoard()
                    ) : viewType === 'calendar' ? (
                        <UniversalCalendarView events={calendarEvents} title="Calendario de experiencia" />
                    ) : viewType === 'gantt' ? (
                        <UniversalGanttView items={ganttItems} moduleName="Experiencia de usuario" />
                    ) : viewType === 'wiki' ? (
                        <UniversalWikiView moduleName="Experiencia de usuario" storageKey="wiki_admin_experience" />
                    ) : (
                    <>
                    {/* Features Grid (The "ClickApps" style) */}
                    <section className="space-y-3">
                        <div className="flex items-center justify-between px-2">
                            <h3 className="font-semibold text-slate-400 uppercase tracking-wide">Módulos y Funcionalidades</h3>
                            <span className="text-[10px] font-bold text-slate-400">Selección Global</span>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {FEATURE_CARDS.map((feature) => {
                                const isEnabled = !!config?.features_enabled?.[feature.id];
                                return (
                                    <div 
                                        key={feature.id}
                                        onClick={() => toggleFeature(feature.id)}
                                        className={clsx(
                                            "p-4 rounded-lg border-2 transition-all cursor-pointer group relative overflow-hidden",
                                            isEnabled 
                                                ? "bg-white dark:bg-white/5 border-blue-600 shadow-2xl shadow-blue-500/10 scale-[1.02]" 
                                                : "bg-slate-50 dark:bg-black/20 border-transparent grayscale opacity-60 hover:grayscale-0 hover:opacity-100"
                                        )}
                                    >
                                        {isEnabled && <div className="absolute top-3 right-6 size-2 rounded-full bg-blue-600 shadow-[0_0_10px_#2563eb]" />}
                                        <div className="space-y-3">
                                            <div className={clsx("size-7 rounded-lg flex items-center justify-center shadow-lg transition-transform group-hover:rotate-12", isEnabled ? "bg-blue-600 text-white" : "bg-white dark:bg-white/10 text-slate-400")}>
                                                <feature.icon size={24} />
                                            </div>
                                            <div>
                                                <h4 className="text-sm font-semibold text-slate-800 dark:text-white uppercase tracking-tight">{feature.label}</h4>
                                                <p className="text-[12px] text-slate-500 dark:text-slate-400 font-medium mt-1 leading-snug">{feature.desc}</p>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </section>

                    {/* UI Engine Personalization */}
                    <section className="space-y-3">
                        <div className="flex items-center justify-between px-2">
                            <h3 className="font-semibold text-slate-400 uppercase tracking-wide">Motor Visual y Marca</h3>
                        </div>
                        
                        <div className="p-4 bg-slate-900 rounded-lg text-white shadow-2xl relative overflow-hidden group border border-white/5">
                            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity"><Palette size={120} /></div>
                            <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-3 items-center">
                                <div className="space-y-3">
                                    <h4 className="text-lg font-bold tracking-tight">Personalización de Marca</h4>
                                    <p className="text-slate-400 text-sm font-medium leading-relaxed italic">&ldquo;Configura el ADN visual de la plataforma para que refleje la identidad de Centro Cristiano de Fe.&rdquo;</p>
                                    <div className="flex gap-4">
                                        <div className="size-10 rounded-full bg-blue-600 cursor-pointer border-2 border-white ring-4 ring-blue-600/20 shadow-xl" />
                                        <div className="size-10 rounded-full bg-sky-600 cursor-pointer hover:scale-110 transition-all" />
                                        <div className="size-10 rounded-full bg-emerald-600 cursor-pointer hover:scale-110 transition-all" />
                                        <div className="size-10 rounded-full bg-rose-600 cursor-pointer hover:scale-110 transition-all" />
                                    </div>
                                </div>
                                <div className="space-y-3 bg-white/5 p-4 rounded-lg border border-white/10 backdrop-blur-md">
                                    <div className="space-y-2">
                                        <label className="text-[9px] font-semibold uppercase text-slate-500 tracking-wide ml-2">Nombre del Workspace</label>
                                        <input type="text" defaultValue="Comunidad Cristiana El Faro" className="w-full bg-black/40 border border-white/10 rounded-lg p-4 text-sm font-bold outline-none focus:border-blue-500 transition-all" />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[9px] font-semibold uppercase text-slate-500 tracking-wide ml-2">URL del Logotipo (SVG/PNG)</label>
                                        <input type="text" placeholder="https://..." className="w-full bg-black/40 border border-white/10 rounded-lg p-4 text-sm font-bold outline-none focus:border-blue-500 transition-all" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>
                    </>
                    )}
                </div>
            </main>
        </div>
    );
}

