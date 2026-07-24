"use client";

import EvangelismShell from '@/components/evangelism/EvangelismShell';
import StrategyCreationDrawer from '@/components/evangelism/StrategyCreationDrawer';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import EmptyState from '@/components/ui/EmptyState';
import { DSSkeleton } from '@/design';
import { useAuth } from '@/context/AuthContext';
import { OPERATIONAL_VIEWS,useViewType } from '@/hooks/useViewType';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import {
Calendar,
ChevronRight,
Flame,
Plus
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback,useEffect,useMemo,useState } from 'react';
import type { Strategy } from './types';

// Antes: este archivo redeclaraba una interfaz EvangelismStrategy local
// que duplicaba (y divergía parcialmente de) Strategy en ./types.ts.
// Centralizamos en ./types.ts para tener un solo contrato UI y reusamos
// aqui con un alias retrocompatible.
export type EvangelismStrategy = Strategy;

export default function EvangelismClient() {
 const { token, loading: authLoading, hasModuleAccess } = useAuth();
 const router = useRouter();
 const { viewType, setViewType } = useViewType('evangelism_dashboard', 'table');
 const [data, setData] = useState<EvangelismStrategy[]>([]);
 const [loading, setLoading] = useState(true);
 const [search, setSearch] = useState('');
 const [isCreateDrawerOpen, setIsCreateDrawerOpen] = useState(false);

 const canReadStrategies = hasModuleAccess('evangelism', 'read');
 const canManageStrategies = hasModuleAccess('evangelism', 'manage');

 const fetchStrategies = useCallback(async () => {
 if (!token || !canReadStrategies) return;
 setLoading(true);
 try {
 const result = await apiFetch<EvangelismStrategy[]>('/evangelism/strategies', { token, silent: true });
 setData(Array.isArray(result) ? result : []);
 } catch {
 setData([]);
 } finally {
 setLoading(false);
 }
 }, [canReadStrategies, token]);

 useEffect(() => {
 if (authLoading) return;
 if (!token || !canReadStrategies) {
 setLoading(false);
 return;
 }
 fetchStrategies();
 }, [authLoading, canReadStrategies, fetchStrategies, token]);

 // Reactively refresh when a new strategy is created globally
 useEffect(() => {
 if (!canReadStrategies) return;
 const handleCreated = () => {
 fetchStrategies();
 };
 window.addEventListener('evangelism-strategy-created', handleCreated);
 return () => {
 window.removeEventListener('evangelism-strategy-created', handleCreated);
 };
 }, [canReadStrategies, fetchStrategies]);

 // El cierre del panel lateral ahora navega a la vista de detalle

 const filteredData = useMemo(() => {
 if (!search) return data;
 const term = search.toLowerCase();
 return data.filter(item => 
 item.name.toLowerCase().includes(term) ||
 (item.description && item.description.toLowerCase().includes(term)) ||
 (item.strategy_type && item.strategy_type.toLowerCase().includes(term))
 );
 }, [data, search]);

 const handleAddItem = () => {
 setIsCreateDrawerOpen(true);
 };

 const handleSelectStrategy = (strat: EvangelismStrategy) => {
 router.push(`/plataforma/evangelism/strategies/${strat.id}`);
 };

 const statusColors = {
 pending: 'hsl(var(--warning))', // amber-500
 active: 'hsl(var(--primary))', // blue-600
 done: 'hsl(var(--success))', // emerald-500
 };

 const statusLabels = {
 pending: 'No iniciada',
 active: 'Iniciada',
 done: 'Terminada',
 };

 const formatDate = (dateStr: string | null | undefined) => {
 if (!dateStr) return 'Sin fecha';
 try {
 const date = new Date(dateStr);
 return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
 } catch {
 return dateStr;
 }
 };

 if (!authLoading && !canReadStrategies) {
 return (
 <ModuleErrorBoundary moduleName="Evangelismo">
 <EvangelismShell
 breadcrumbs={[
 { label: 'Evangelismo', icon: Flame },
 { label: 'Estrategias' }
 ]}
 >
 <div className="min-h-[60vh] flex items-center justify-center p-3">
 <div className="max-w-md w-full rounded-lg border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning-muted))] px-3 py-8 text-center">
 <h2 className="text-lg font-bold text-[hsl(var(--warning))]">Acceso restringido</h2>
 <p className="mt-2 text-sm font-medium text-[hsl(var(--warning))]">
 Esta vista requiere permisos de lectura sobre evangelismo.
 </p>
 </div>
 </div>
 </EvangelismShell>
 </ModuleErrorBoundary>
 );
 }

 return (
 <ModuleErrorBoundary moduleName="Evangelismo">
 <EvangelismShell
 breadcrumbs={[
 { label: 'Evangelismo', icon: Flame },
 { label: 'Estrategias' }
 ]}
 viewOptions={OPERATIONAL_VIEWS}
 viewType={viewType}
 onViewChange={setViewType}
 onSearch={setSearch}
 rightActions={
 canManageStrategies ? (
 <button
 onClick={handleAddItem}
 className="h-7 px-3 text-[11px] font-bold flex items-center gap-1.5 bg-[hsl(var(--primary))] hover:opacity-90 text-white rounded-[7px] transition-all shadow-sm"
 >
 <Plus size={12} />
 Crear estrategia
 </button>
 ) : null
 }
 >
 <div className="h-full flex flex-col relative">
 {loading ? (
 <div className="p-4 space-y-4">
 {[1, 2, 3].map(i => <DSSkeleton key={i} className="h-8 w-full rounded-lg" />)}
 </div>
 ) : filteredData.length === 0 ? (
 <EmptyState
 title="No hay estrategias"
 description="Las estrategias te permiten planificar campañas de alcance, consolidación y discipulado en tu comunidad."
 icon={Flame}
 onAction={canManageStrategies ? handleAddItem : undefined}
 actionLabel={canManageStrategies ? "Crear estrategia" : undefined}
 />
 ) : (
 <div className="pb-16 flex-1">
 {/* ── TABLE VIEW ─────────────────────────────── */}
 {viewType === 'table' && (
 <div className="overflow-x-auto border border-[hsl(var(--border-primary))] dark:border-white/[0.06] rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))]">
 <table className="w-full text-left border-collapse">
 <thead>
 <tr className="border-b border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))]/50 dark:bg-black/10">
 <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] w-16">ID</th>
 <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Estrategia</th>
 <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] w-32">Estado</th>
 <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] w-44">Tipo</th>
 <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] w-40">Inicio</th>
 <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] w-40">Fin</th>
 <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] w-12"></th>
 </tr>
 </thead>
 <tbody className="divide-y divide-[hsl(var(--border-primary))]">
 {filteredData.map((strategy, idx) => (
 <motion.tr 
 key={strategy.id}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: idx * 0.03, duration: 0.2 }}
 onClick={() => handleSelectStrategy(strategy)}
 className="hover:bg-[hsl(var(--bg-muted))] cursor-pointer group transition-colors"
 >
 <td className="px-3 py-1.5 text-[12px] font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
 {strategy.codigo ? strategy.codigo : `#${strategy.id}`}
 </td>
 <td className="px-3 py-1.5">
 <div className="text-[12px] font-bold text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--primary))] transition-colors">
 {strategy.name}
 </div>
 {strategy.description && (
 <div className="text-[11px] text-[hsl(var(--text-secondary))] font-medium truncate max-w-[300px] mt-0.5">
 {strategy.description}
 </div>
 )}
 </td>
 <td className="px-3 py-1.5">
 <span 
 className="px-2.5 py-1 rounded-full text-[10px] font-bold"
 style={{ 
 backgroundColor: `${statusColors[strategy.status]}12`, 
 color: statusColors[strategy.status] 
 }}
 >
 {statusLabels[strategy.status]}
 </span>
 </td>
 <td className="px-3 py-1.5 text-[12px] font-semibold text-[hsl(var(--text-secondary))]">
 {strategy.strategy_type || 'General'}
 </td>
 <td className="px-3 py-1.5 text-[12px] text-[hsl(var(--text-secondary))] font-medium">
 {formatDate(strategy.start_date)}
 </td>
 <td className="px-3 py-1.5 text-[12px] text-[hsl(var(--text-secondary))] font-medium">
 {formatDate(strategy.end_date)}
 </td>
 <td className="px-3 py-1.5 text-right">
 <ChevronRight size={16} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-secondary))] dark:group-hover:text-white transition-all transform group-hover:translate-x-0.5" />
 </td>
 </motion.tr>
 ))}
 </tbody>
 </table>
 </div>
 )}

 {/* ── BOARD VIEW ─────────────────────────────── */}
 {viewType === 'board' && (
 <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 h-full min-h-48 items-start">
 {/* Columns map */}
 {(['pending', 'active', 'done'] as const).map(colStatus => {
 const colItems = filteredData.filter(item => item.status === colStatus);
 return (
 <div 
 key={colStatus}
 className="bg-[hsl(var(--bg-secondary))] border border-[hsl(var(--border-primary))] rounded-lg p-4 flex flex-col max-h-[80vh] overflow-y-auto scrollbar-thin"
 >
 <header className="flex items-center justify-between mb-4 px-2 shrink-0">
 <div className="flex items-center gap-2">
 <span 
 className="size-2.5 rounded-full" 
 style={{ backgroundColor: statusColors[colStatus] }}
 />
 <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[hsl(var(--text-primary))]">
 {statusLabels[colStatus]}
 </h3>
 </div>
 <span className="font-semibold bg-[hsl(var(--bg-muted))] px-2 py-0.5 rounded-md text-[hsl(var(--text-secondary))]">
 {colItems.length}
 </span>
 </header>

 <div className="space-y-4">
 {colItems.map((strategy) => (
 <motion.div
 key={strategy.id}
 initial={{ opacity: 0, scale: 0.96 }}
 animate={{ opacity: 1, scale: 1 }}
 transition={{ duration: 0.2 }}
 onClick={() => handleSelectStrategy(strategy)}
 className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border-primary))]/70 p-3 shadow-sm hover:shadow-xl hover:shadow-black/10 dark:hover:shadow-black/30 transition-all duration-300 cursor-pointer overflow-hidden active:scale-[0.99] border-t-4"
 style={{ borderTopColor: statusColors[strategy.status] }}
 >
 <div className="flex items-start justify-between gap-4">
 <h4 className="text-[13px] font-bold text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--primary))] transition-colors">
 {strategy.name}
 </h4>
 <span className="font-semibold text-[hsl(var(--text-secondary))] shrink-0">
 {strategy.codigo ? strategy.codigo : `#${strategy.id}`}
 </span>
 </div>

 {strategy.description && (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-2 font-medium line-clamp-2 leading-relaxed">
 {strategy.description}
 </p>
 )}

 <div className="mt-4 pt-3 border-t border-[hsl(var(--border-primary))] flex flex-wrap gap-2 items-center justify-between">
 <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[9px] font-semibold uppercase tracking-wide bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]">
 {strategy.strategy_type || 'General'}
 </span>
 
 <div className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-secondary))] font-bold">
 <Calendar size={11} />
 <span>{formatDate(strategy.start_date).split(' ')[0]}</span>
 <span>-</span>
 <span>{formatDate(strategy.end_date).split(' ')[0]}</span>
 </div>
 </div>
 </motion.div>
 ))}

 {colItems.length === 0 && (
 <div className="py-8 text-center border border-dashed border-[hsl(var(--border-primary))] rounded-lg text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 Vacío
 </div>
 )}
 </div>
 </div>
 );
 })}
 </div>
 )}

 {/* ── LIST VIEW ─────────────────────────────── */}
 {viewType === 'list' && (
 <div className="space-y-4 w-full">
 {filteredData.map((strategy, idx) => (
 <motion.div
 key={strategy.id}
 initial={{ opacity: 0, y: 12 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: idx * 0.03 }}
 onClick={() => handleSelectStrategy(strategy)}
 className="group bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border-primary))]/70 p-3 shadow-sm hover:shadow-xl hover:shadow-black/10 dark:hover:shadow-black/30 transition-all duration-300 cursor-pointer flex items-center justify-between gap-3"
 >
 <div className="flex items-start gap-4 flex-1 min-w-0">
 <div 
 className="size-10 rounded-md flex items-center justify-center shrink-0"
 style={{ backgroundColor: `${statusColors[strategy.status]}12`, color: statusColors[strategy.status] }}
 >
 <Flame size={20} />
 </div>
 <div className="min-w-0 flex-1">
 <div className="flex items-center gap-3">
 <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--primary))] transition-colors">
 {strategy.name}
 </h3>
 <span className="font-semibold bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] px-2 py-0.5 rounded">
 #{strategy.id}
 </span>
 </div>
 {strategy.description && (
 <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1 font-medium line-clamp-1">
 {strategy.description}
 </p>
 )}
 <div className="flex items-center gap-4 mt-2 text-[10px] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wider">
 <span>Tipo: {strategy.strategy_type || 'General'}</span>
 <span>•</span>
 <span>Inicio: {formatDate(strategy.start_date)}</span>
 <span>•</span>
 <span>Fin: {formatDate(strategy.end_date)}</span>
 </div>
 </div>
 </div>

 <div className="flex items-center gap-4">
 <span 
 className="px-2.5 py-1 rounded-full text-[10px] font-bold shrink-0"
 style={{ 
 backgroundColor: `${statusColors[strategy.status]}12`, 
 color: statusColors[strategy.status] 
 }}
 >
 {statusLabels[strategy.status]}
 </span>
 <ChevronRight size={18} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-secondary))] dark:group-hover:text-white transition-all transform group-hover:translate-x-0.5" />
 </div>
 </motion.div>
 ))}
 </div>
 )}
 </div>
 )}
 </div>

 {/* ── Strategy Creation Drawer ── */}
 {canManageStrategies ? (
 <StrategyCreationDrawer
 isOpen={isCreateDrawerOpen}
 onClose={() => setIsCreateDrawerOpen(false)}
 onCreated={fetchStrategies}
 />
 ) : null}
 </EvangelismShell>
 </ModuleErrorBoundary>
 );
}
