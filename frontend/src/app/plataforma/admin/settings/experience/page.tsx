"use client";

import React, { useState, useEffect } from 'react';
import { SITE_NAME } from '@/lib/site-config';
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
    { id: 'gantt', label: 'Vista de Gantt', desc: 'Habilita el cronograma interactivo en proyectos.', icon: GanttChart, color: 'text-[hsl(var(--primary))]' },
    { id: 'ai_coach', label: 'Optimus Brain Coach', desc: 'Asistente de IA para academia y CRM.', icon: Bot, color: 'text-sky-500' },
    { id: 'call_center', label: 'Call Center Pastoral', icon: Smartphone, desc: 'Gestión de llamadas y mensajes masivos.', color: 'text-amber-500' },
    { id: 'prayer_wall', label: 'Muro de Intercesión', icon: Heart, desc: 'Registro público de peticiones de oración.', color: 'text-[hsl(var(--destructive))]' },
    { id: 'kanban', label: 'Tableros Kanban', icon: KanbanSquare, desc: 'Visualización de procesos por arrastre.', color: 'text-[hsl(var(--success))]' },
    { id: 'audit_logs', label: 'Auditoría de Staff', icon: Shield, desc: 'Registro detallado de acciones administrativas.', color: 'text-[hsl(var(--primary))]' },
];
const EXPERIENCE_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function WorkspaceExperienceManager() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    interface WorkspaceConfig {
    features_enabled?: Record<string, boolean>;
    feature_rules?: Record<string, unknown>;
    health?: Record<string, string>;
}
    const [config, setConfig] = useState<WorkspaceConfig | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        const controller = new AbortController();
        const fetchConfig = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<WorkspaceConfig>('/workspace/config', { token, signal: controller.signal });
                setConfig(data);
            } catch (err) {
                if (controller.signal.aborted) return;
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchConfig();
        return () => controller.abort();
    }, [token]);

    const toggleFeature = (id: string) => {
        setConfig((prev) => ({
            ...(prev ?? {}),
            features_enabled: {
                ...(prev?.features_enabled ?? {}),
                [id]: !prev?.features_enabled?.[id]
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

    if (loading) return <div className="p-4 text-center text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide animate-pulse">Cargando Brain...</div>;

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
                <button key={feature.id} onClick={() => toggleFeature(feature.id)} className="w-full text-left bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 flex items-center justify-between gap-3 hover:border-blue-300 transition-all">
                    <div className="flex items-center gap-3">
                        <div className={clsx("size-7 rounded-lg flex items-center justify-center", feature.enabled ? "bg-[hsl(var(--primary))] text-white" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]")}>
                            <feature.icon size={24} />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{feature.label}</h3>
                            <p className="mt-1 text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{feature.desc}</p>
                        </div>
                    </div>
                    <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", feature.enabled ? "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]")}>{feature.enabled ? 'Activo' : 'Inactivo'}</span>
                </button>
            ))}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto bg-[hsl(var(--bg-primary))] dark:bg-white/5">
            <table className="w-full min-w-[480px] text-left">
                <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Feature</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Descripción</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Estado</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                    {featureRows.map((feature) => (
                        <tr key={feature.id} onClick={() => toggleFeature(feature.id)} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.03] cursor-pointer">
                            <td className="px-3 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{feature.label}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{feature.desc}</td>
                            <td className="px-3 py-1.5"><span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", feature.enabled ? "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]")}>{feature.enabled ? 'Activo' : 'Inactivo'}</span></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {groupedFeatures.map((group) => (
                <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{group.label}</span>
                        <span className="font-semibold text-[hsl(var(--text-secondary))]">{group.rows.length}</span>
                    </div>
                    <div className="space-y-3">
                        {group.rows.map((feature) => (
                            <button key={feature.id} onClick={() => toggleFeature(feature.id)} className="w-full text-left bg-[hsl(var(--bg-primary))] dark:bg-white/[0.05] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 hover:border-blue-300 transition-all">
                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{feature.label}</p>
                                <p className="mt-2 text-[10px] font-bold text-[hsl(var(--text-secondary))]">{feature.desc}</p>
                            </button>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Ajustes', icon: Settings }, { label: 'Experiencia de Usuario', icon: Sparkles }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={EXPERIENCE_VIEWS}
                rightActions={
                    <div className="flex items-center gap-2">
                        <button onClick={() => router.back()} className="px-4 py-2 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide hover:text-[hsl(var(--text-primary))]">Cancelar</button>
                        <button 
                            onClick={handleSave} disabled={isSaving}
                            className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl active:scale-95 transition-all"
                        >
                            {isSaving ? <RotateCcw className="animate-spin" size={14} /> : <Save size={14} />} Guardar Workspace
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-3 lg:p-4 relative pb-4">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_hsl(var(--primary)/0.05)_0%,_transparent_50%)] pointer-events-none" />

 <div className="w-full space-y-3 relative z-10">
                    
                    {/* Header */}
                    <header className="space-y-4">
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-sky-50 dark:bg-sky-900/20 text-sky-600 rounded-lg text-[10px] font-semibold uppercase tracking-wide border border-sky-100 dark:border-sky-900/30">
                            <Zap size={14} /> Workspace Experience Manager v3.0
                        </div>
                        <h1 className="text-lg lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">
                            El cerebro de tu <span className="text-[hsl(var(--primary))] italic">interfaz.</span>
                        </h1>
                        <p className="text-xl text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium max-w-2xl leading-relaxed">
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
                            <h3 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Módulos y Funcionalidades</h3>
                            <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">Selección Global</span>
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
                                                ? "bg-[hsl(var(--bg-primary))] dark:bg-white/5 border-blue-600 shadow-2xl shadow-blue-500/10 scale-[1.02]" 
                                                : "bg-[hsl(var(--surface-1))] dark:bg-black/20 border-transparent grayscale opacity-60 hover:grayscale-0 hover:opacity-100"
                                        )}
                                    >
                                        {isEnabled && <div className="absolute top-3 right-6 size-2 rounded-full bg-[hsl(var(--primary))] shadow-[0_0_10px_#2563eb]" />}
                                        <div className="space-y-3">
                                            <div className={clsx("size-7 rounded-lg flex items-center justify-center shadow-lg transition-transform group-hover:rotate-12", isEnabled ? "bg-[hsl(var(--primary))] text-white" : "bg-[hsl(var(--bg-primary))] dark:bg-white/10 text-[hsl(var(--text-secondary))]")}>
                                                <feature.icon size={24} />
                                            </div>
                                            <div>
                                                <h4 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{feature.label}</h4>
                                                <p className="text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium mt-1 leading-snug">{feature.desc}</p>
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
                            <h3 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Motor Visual y Marca</h3>
                        </div>
                        
                        <div className="p-4 bg-[hsl(var(--bg-muted))] rounded-lg text-white shadow-2xl relative overflow-hidden group border border-white/5">
                            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity"><Palette size={120} /></div>
                            <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-3 items-center">
                                <div className="space-y-3">
                                    <h4 className="text-lg font-bold tracking-tight">Personalización de Marca</h4>
                                    <p className="text-[hsl(var(--text-secondary))] text-sm font-medium leading-relaxed italic">&ldquo;Configura el ADN visual de la plataforma para que refleje la identidad de Centro Cristiano de Fe.&rdquo;</p>
                                    <div className="flex gap-4">
                                        <div className="size-10 rounded-full bg-[hsl(var(--primary))] cursor-pointer border-2 border-white ring-4 ring-blue-600/20 shadow-xl" />
                                        <div className="size-10 rounded-full bg-sky-600 cursor-pointer hover:scale-110 transition-all" />
                                        <div className="size-10 rounded-full bg-emerald-600 cursor-pointer hover:scale-110 transition-all" />
                                        <div className="size-10 rounded-full bg-rose-600 cursor-pointer hover:scale-110 transition-all" />
                                    </div>
                                </div>
                                <div className="space-y-3 bg-white/5 p-4 rounded-lg border border-white/10 backdrop-blur-md">
                                    <div className="space-y-2">
                                        <label className="text-[9px] font-semibold uppercase text-[hsl(var(--text-secondary))] tracking-wide ml-2">Nombre del Workspace</label>
                                        <input type="text" defaultValue={SITE_NAME} className="w-full bg-black/40 border border-white/10 rounded-lg p-4 text-sm font-bold outline-none focus:border-blue-500 transition-all" />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[9px] font-semibold uppercase text-[hsl(var(--text-secondary))] tracking-wide ml-2">URL del Logotipo (SVG/PNG)</label>
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

