"use client";

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { 
    Package, Plus, CheckCircle2, Wrench, AlertTriangle, ChevronRight,
    Box, Cog, History, ShieldCheck, Zap, Tag, QrCode
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { motion, AnimatePresence } from 'framer-motion';
import { DSMetric } from '@/design/components/DSMetric';
import { DSChart } from '@/design/components/DSChart';
import { DSCard } from '@/design/components/DSCard';
import { toast } from 'sonner';
import clsx from 'clsx';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import Skeleton from '@/components/ui/Skeleton';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ViewType } from '@/components/ViewSwitcher';

const INVENTORY_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function AdminInventoryPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [assets, setAssets] = useState<any[]>([]);
    const [dashboard, setDashboard] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [viewType, setViewType] = useState<ViewType>('table');
    const [selectedAsset, setSelectedAsset] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [data, dbData] = await Promise.all([
                apiFetch<any[]>('/assets/', { token, cache: 'no-store' }),
                apiFetch<any>('/dashboard/assets', { token, cache: 'no-store' })
            ]);
            setAssets(Array.isArray(data) ? data : []);
            setDashboard(dbData);
        } catch (e) { 
            console.error(e);
            toast.error("Error al cargar inventario");
        } finally { 
            setLoading(false); 
        }
    }, [token]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleOpenAsset = (asset: any) => {
        setSelectedAsset(asset);
        setIsDrawerOpen(true);
    };

    const stats = {
        total: assets.length,
        operativo: assets.filter(a => a.current_status === 'Disponible').length,
        mantenimiento: assets.filter(a => a.current_status === 'Mantenimiento').length,
        daniado: assets.filter(a => a.current_status === 'Dañado').length,
    };
    const filteredAssets = useMemo(() => assets.filter((asset) =>
        [asset.name, asset.brand, asset.category, asset.current_status, asset.serial_number]
            .some((field) => String(field ?? '').toLowerCase().includes(searchTerm.toLowerCase()))
    ), [assets, searchTerm]);
    const groupedAssets = useMemo(() => {
        const statuses = ['Disponible', 'Mantenimiento', 'Dañado', 'Asignado'];
        return statuses.map((status) => ({
            status,
            items: filteredAssets.filter((asset) => (asset.current_status || 'Disponible') === status),
        })).filter((column) => column.items.length > 0 || ['Disponible', 'Mantenimiento'].includes(column.status));
    }, [filteredAssets]);
    const calendarEvents = useMemo(() => filteredAssets.map((asset) => ({
        id: asset.id,
        title: asset.name,
        date: (asset.updated_at || asset.created_at || new Date().toISOString()).slice(0, 10),
        color: asset.current_status === 'Disponible' ? 'emerald' as const : asset.current_status === 'Dañado' ? 'rose' as const : 'amber' as const,
        location: asset.category,
    })), [filteredAssets]);
    const ganttItems = useMemo(() => filteredAssets.map((asset) => ({
        id: asset.id,
        title: asset.name,
        subtitle: asset.current_status || asset.category,
        start_date: (asset.created_at || new Date().toISOString()).slice(0, 10),
        end_date: (asset.updated_at || asset.created_at || new Date().toISOString()).slice(0, 10),
        color: asset.current_status === 'Disponible' ? 'emerald' as const : asset.current_status === 'Dañado' ? 'rose' as const : 'amber' as const,
        progress: asset.current_status === 'Disponible' ? 100 : asset.current_status === 'Mantenimiento' ? 60 : 25,
    })), [filteredAssets]);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <style jsx global>{`
                .aura-industrial {
                    position: relative;
                }
                .aura-industrial::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, transparent), transparent 50%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .aura-industrial:hover::after {
                    opacity: 1;
                }
                .shimmer-asset {
                    position: relative;
                    overflow: hidden;
                }
                .shimmer-asset::after {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 40%;
                    height: 100%;
                    background: linear-gradient(
                        90deg,
                        transparent,
                        rgba(255, 255, 255, 0.08),
                        transparent
                    );
                    animation: asset-shimmer 4s infinite;
                }
                @keyframes asset-shimmer {
                    0% { left: -100%; }
                    100% { left: 250%; }
                }
                .stacked-glass-inventory {
                    background: rgba(255, 255, 255, 0.7);
                    backdrop-filter: blur(24px) saturate(180%);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
                .dark .stacked-glass-inventory {
                    background: rgba(30, 31, 33, 0.85);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Infraestructura', icon: Package }, { label: 'Inventario de Activos', icon: Box }]}
                viewType={viewType} setViewType={setViewType} availableViews={INVENTORY_VIEWS} onSearch={setSearchTerm}
                rightActions={
                    <div className="flex items-center gap-2">
                        <button className="flex items-center gap-2 px-3 py-2 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 rounded-[1.25rem] text-[11px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300 transition-all"><QrCode size={14} /> Escanear QR</button>
                        <button className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-[1.25rem] text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-blue-700 transition-all"><Plus size={14} /> Nuevo Activo</button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-3 lg:p-4 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-[1400px] mx-auto space-y-3 relative z-10">
                    {/* Cinematic Header Stats */}
                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                                {[1,2,3,4].map(i => <Skeleton key={i} className="h-32 rounded-lg" />)}
                            </div>
                        ) : (
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="grid grid-cols-1 md:grid-cols-4 gap-3"
                            >
                                <InventoryStat title="Total Activos" value={stats.total} icon={Package} auraColor="rgba(100, 116, 139, 0.2)" />
                                <InventoryStat title="Operativos" value={stats.operativo} icon={CheckCircle2} color="text-emerald-500" auraColor="rgba(16, 185, 129, 0.2)" />
                                <InventoryStat title="En Revisión" value={stats.mantenimiento} icon={Wrench} color="text-amber-500" auraColor="rgba(245, 158, 11, 0.2)" />
                                <InventoryStat title="Fuera de Uso" value={stats.daniado} icon={AlertTriangle} color="text-rose-500" auraColor="rgba(244, 63, 94, 0.2)" />
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Industrial Asset List */}
                    <div className="bg-white dark:bg-[#1e1f21] rounded-lg border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm">
                        {loading ? (
                            <div className="p-4 space-y-4">
                                {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-8 w-full rounded-lg" />)}
                            </div>
                        ) : viewType === 'table' ? (
                            <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5">
                                            <th className="px-4 py-2 font-semibold text-slate-400 uppercase tracking-wide">Identificación Activo</th>
                                            <th className="px-4 py-2 font-semibold text-slate-400 uppercase tracking-wide">Especificaciones</th>
                                            <th className="px-4 py-2 font-semibold text-slate-400 uppercase tracking-wide">Estado Operativo</th>
                                            <th className="px-4 py-2 font-semibold text-slate-400 uppercase tracking-wide text-right">Detalles</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                        {filteredAssets.map((asset, i) => (
                                            <motion.tr 
                                                key={i}
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: i * 0.03 }}
                                                onClick={() => handleOpenAsset(asset)}
                                                className="group hover:bg-slate-50 dark:hover:bg-white/5 transition-all cursor-pointer"
                                            >
                                                <td className="px-4 py-2">
                                                    <div className="flex items-center gap-3">
                                                        <div className="size-7 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-all duration-500 shadow-inner">
                                                            <Box size={24} />
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-semibold text-slate-800 dark:text-slate-100 uppercase tracking-tight leading-none mb-1">{asset.name}</div>
                                                            <div className="font-semibold text-blue-500 uppercase tracking-wide">ID: {asset.serial_number || 'INTERNO-00'+asset.id}</div>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-2">
                                                    <div className="flex flex-col gap-1">
                                                        <div className="text-sm font-bold text-slate-600 dark:text-slate-300 flex items-center gap-2">
                                                            <Tag size={12} className="text-slate-400" />
                                                            {asset.brand || 'Genérico'}
                                                        </div>
                                                        <div className="font-semibold text-slate-400 uppercase tracking-wide">Categoría: {asset.category || 'Mobiliario'}</div>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-2">
                                                    <div className="flex items-center gap-3">
                                                        <div className={clsx(
                                                            "size-2 rounded-full shadow-[0_0_8px_currentColor] animate-pulse",
                                                            asset.current_status === 'Disponible' ? "text-emerald-500" : "text-amber-500"
                                                        )} />
                                                        <span className={clsx(
                                                            "text-[10px] font-semibold uppercase tracking-wide",
                                                            asset.current_status === 'Disponible' ? "text-emerald-600" : "text-amber-600"
                                                        )}>
                                                            {asset.current_status}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-2 text-right">
                                                    <button className="p-2.5 bg-slate-50 dark:bg-white/5 text-slate-400 rounded-md group-hover:bg-blue-50 group-hover:text-blue-600 transition-all transform group-hover:translate-x-1 shadow-sm">
                                                        <ChevronRight size={18} />
                                                    </button>
                                                </td>
                                            </motion.tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : viewType === 'list' ? (
                            <div className="divide-y divide-slate-100 dark:divide-white/5">
                                {filteredAssets.map((asset) => (
                                    <button key={asset.id} onClick={() => handleOpenAsset(asset)} className="flex w-full items-center justify-between gap-4 px-4 py-2 text-left hover:bg-slate-50 dark:hover:bg-white/5">
                                        <div>
                                            <p className="text-sm font-semibold text-slate-900 dark:text-white">{asset.name}</p>
                                            <p className="text-xs font-semibold text-slate-400">{asset.category || 'Sin categoria'} - {asset.brand || 'Generico'}</p>
                                        </div>
                                        <span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:bg-white/10">{asset.current_status || 'Disponible'}</span>
                                    </button>
                                ))}
                            </div>
                        ) : viewType === 'grid' ? (
                            <div className="grid grid-cols-1 gap-4 p-3 md:grid-cols-2 xl:grid-cols-3">
                                {filteredAssets.map((asset) => (
                                    <button key={asset.id} onClick={() => handleOpenAsset(asset)} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-left transition hover:border-blue-300 dark:border-white/10 dark:bg-white/[0.03]">
                                        <Box className="mb-4 text-blue-500" size={24} />
                                        <p className="text-sm font-semibold text-slate-900 dark:text-white">{asset.name}</p>
                                        <p className="mt-1 text-xs font-semibold text-slate-400">{asset.serial_number || `INTERNO-${asset.id}`}</p>
                                    </button>
                                ))}
                            </div>
                        ) : viewType === 'board' || viewType === 'kanban' ? (
                            <div className="flex gap-4 overflow-x-auto p-3">
                                {groupedAssets.map((column) => (
                                    <section key={column.status} className="w-80 shrink-0 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                                        <div className="mb-3 flex items-center justify-between px-1">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{column.status}</p>
                                            <span className="font-semibold text-slate-400">{column.items.length}</span>
                                        </div>
                                        <div className="space-y-2">
                                            {column.items.map((asset) => (
                                                <button key={asset.id} onClick={() => handleOpenAsset(asset)} className="w-full rounded-md border border-slate-200 bg-white p-3 text-left dark:border-white/10 dark:bg-white/5">
                                                    <p className="text-xs font-semibold text-slate-900 dark:text-white">{asset.name}</p>
                                                    <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{asset.category || 'Activo'}</p>
                                                </button>
                                            ))}
                                        </div>
                                    </section>
                                ))}
                            </div>
                        ) : viewType === 'calendar' ? (
                            <div className="h-[720px] p-3"><UniversalCalendarView events={calendarEvents} title="Calendario de inventario" /></div>
                        ) : viewType === 'gantt' ? (
                            <div className="h-[720px] p-3"><UniversalGanttView items={ganttItems} moduleName="Inventario" /></div>
                        ) : (
                            <div className="p-3"><UniversalWikiView moduleName="Inventario" storageKey="wiki_admin_inventory" /></div>
                        )}
                    </div>
                </div>
            </main>

            {/* Asset Details Cinematic Drawer */}
            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedAsset?.name || 'Ficha Técnica'}
                subtitle={`ACTIVO REF-${selectedAsset?.id || '000'}`}
                actions={<><button className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-blue-600 hover:bg-blue-50 rounded-md transition-all">Editar</button><button className="px-3 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl">Programar Revisión</button></>}
            >
                <div className="space-y-3 animate-in fade-in slide-in-from-right-4 duration-500">
                    {/* Status Shimmer Card */}
                    <div className="p-4 rounded-lg bg-slate-900 text-white shadow-2xl relative overflow-hidden group border border-white/5 shimmer-asset">
                        <div className="absolute top-0 right-0 p-3 opacity-10 rotate-12 group-hover:scale-110 transition-transform"><ShieldCheck size={100} /></div>
                        <div className="relative z-10 space-y-4">
                            <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 backdrop-blur-xl border border-white/10 rounded-full text-[9px] font-semibold uppercase tracking-wide">
                                <ShieldCheck size={12} className="text-emerald-400" /> Verificación Certificada
                            </div>
                            <div>
                                <p className="font-semibold text-slate-400 uppercase tracking-wide mb-1">Estado de Salud del Activo</p>
                                <h3 className="text-xl font-bold tracking-tight">{selectedAsset?.current_status === 'Disponible' ? 'ÓPTIMO' : 'EN REVISIÓN'}</h3>
                            </div>
                            <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                                <motion.div 
                                    initial={{ width: 0 }} 
                                    animate={{ width: selectedAsset?.current_status === 'Disponible' ? '100%' : '60%' }} 
                                    className={clsx("h-full", selectedAsset?.current_status === 'Disponible' ? "bg-emerald-500" : "bg-amber-500")} 
                                />
                            </div>
                        </div>
                    </div>

                    {/* Technical Specs Stacked Glass */}
                    <div className="space-y-3">
                        <h4 className="font-semibold text-slate-400 uppercase tracking-wide px-2 flex items-center gap-3">
                            <Cog size={16} className="text-blue-500" /> Especificaciones de Fábrica
                        </h4>
                        <div className="grid grid-cols-2 gap-4">
                            <SpecItem label="Marca / Fabricante" value={selectedAsset?.brand || 'No especificado'} icon={Zap} />
                            <SpecItem label="Número de Serie" value={selectedAsset?.serial_number || 'S/N'} icon={QrCode} />
                            <SpecItem label="Fecha de Adquisición" value="Marzo 2026" icon={History} />
                            <SpecItem label="Valor Activo" value="$450,000" icon={Tag} />
                        </div>
                    </div>

                    {/* Maintenance Log */}
                    <div className="space-y-3 pt-6 border-t border-slate-100 dark:border-white/5">
                        <div className="flex items-center justify-between px-2">
                            <h4 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-3">
                                <History size={16} className="text-blue-500" /> Registro de Mantenimiento
                            </h4>
                            <button className="text-[10px] font-semibold uppercase text-blue-600 hover:underline">Ver todo</button>
                        </div>
                        <div className="space-y-4">
                            {[1, 2].map(i => (
                                <div key={i} className="p-3 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/10 flex items-center justify-between group/log hover:bg-white hover:shadow-sm transition-all">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-md bg-white dark:bg-white/10 flex items-center justify-center text-slate-400 border border-slate-100 dark:border-white/10 shadow-sm"><Wrench size={18} /></div>
                                        <div>
                                            <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-tight">Revisión Preventiva {i}</p>
                                            <p className="text-[10px] font-bold text-slate-400">12 de Feb, 2026</p>
                                        </div>
                                    </div>
                                    <CheckCircle2 size={16} className="text-emerald-500 opacity-0 group-hover/log:opacity-100 transition-opacity" />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function InventoryStat({ title, value, icon: Icon, color = "text-slate-800", auraColor }: any) {
    return (
        <div 
            className="aura-industrial p-4 rounded-lg bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm group hover:shadow-2xl transition-all duration-500 relative overflow-hidden"
            style={{ '--aura-color': auraColor } as any}
        >
            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 group-hover:scale-125 group-hover:rotate-12 transition-all duration-700"><Icon size={56} /></div>
            <div className="space-y-4 relative z-10">
                <p className="font-semibold text-slate-400 uppercase tracking-wide">{title}</p>
                <h3 className={clsx("text-lg font-bold tracking-tighter leading-none dark:text-white", color)}>{value}</h3>
                <div className="flex items-center gap-2">
                    <div className="h-1 w-12 bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-current opacity-30 w-3/4"></div>
                    </div>
                    <span className="font-semibold text-slate-400 uppercase tracking-wide">Sincronizado</span>
                </div>
            </div>
        </div>
    );
}

function SpecItem({ label, value, icon: Icon }: any) {
    return (
        <div className="p-3 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-lg transition-all hover:bg-white hover:shadow-sm group/spec">
            <div className="flex items-center gap-2 mb-2"><Icon size={14} className="text-slate-400 group-hover/spec:text-blue-500 transition-colors" /><span className="font-semibold text-slate-400 uppercase tracking-wide">{label}</span></div>
            <p className="font-semibold text-slate-800 dark:text-white uppercase tracking-tight">{value}</p>
        </div>
    );
}

