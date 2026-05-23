"use client";

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { 
    Heart, Mail, Phone, Star, GraduationCap, ChevronRight, 
    Calendar
} from 'lucide-react';

interface Member {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    church_role: string;
    spiritual_status: string;
    spiritual_health: number;
    academy_progress: number;
    created_at: string;
}

interface CrmViewProps {
    members: Member[];
    onSelect?: (member: Member) => void;
}

// ----------------------------------------------------------------------
// 1. GRID VIEW (Classic Cards)
// ----------------------------------------------------------------------

export function CrmGridView({ members, onSelect }: CrmViewProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {members.map((member, idx) => (
                <MemberCard 
                    key={member.id} 
                    member={member} 
                    index={idx}
                    onClick={() => onSelect?.(member)}
                />
            ))}
        </div>
    );
}

// Re-using the MemberCard layout for Grid View
function MemberCard({ member, index, onClick }: { member: Member, index: number, onClick: () => void }) {
    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.02 }}
            onClick={onClick}
            className="group p-4 rounded-md bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 hover:border-blue-500/50 hover:shadow-2xl transition-all cursor-pointer relative overflow-hidden"
        >
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-4">
                    <div className="size-8 rounded-lg bg-gradient-to-br from-slate-100 to-slate-200 dark:from-white/10 dark:to-white/5 flex items-center justify-center text-slate-400 group-hover:from-blue-600 group-hover:to-blue-700 group-hover:text-white transition-all shadow-sm">
                        <span className="text-base font-bold">{(member.first_name?.[0] || '')}{(member.last_name?.[0] || '')}</span>
                    </div>
                    <div>
                        <h4 className="text-base font-bold text-slate-900 dark:text-white leading-none mb-1 truncate max-w-[150px]">
                            {member.first_name} {member.last_name}
                        </h4>
                        <span className="px-2 py-0.5 rounded-lg bg-slate-100 dark:bg-white/5 text-[9px] font-bold uppercase tracking-wide text-slate-500">
                            {member.church_role || 'Miembro'}
                        </span>
                    </div>
                </div>
                <div className="flex items-center gap-1 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                    <Heart size={12} className="text-blue-600" fill="currentColor" />
                    <span className="text-[10px] font-bold text-blue-600">{Math.round((member.spiritual_health || 0.8) * 100)}%</span>
                </div>
            </div>

            <div className="space-y-3 mb-3">
                <div className="flex items-center gap-3 text-slate-400">
                    <Mail size={14} />
                    <span className="text-xs font-bold truncate">{member.email || 'Sin correo'}</span>
                </div>
                <div className="flex items-center gap-3 text-slate-400">
                    <Phone size={14} />
                    <span className="text-xs font-bold">{member.phone || 'Sin teléfono'}</span>
                </div>
            </div>

            <div className="pt-4 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                <div className="flex -space-x-2">
                    <div className="size-6 rounded-full bg-emerald-100 border-2 border-white dark:border-[#1e1f21] flex items-center justify-center text-emerald-600"><Star size={10} fill="currentColor" /></div>
                    <div className="size-6 rounded-full bg-blue-100 border-2 border-white dark:border-[#1e1f21] flex items-center justify-center text-blue-600"><GraduationCap size={10} /></div>
                </div>
                <span className="text-[9px] font-bold uppercase text-slate-400">Ver Perfil <ChevronRight size={10} className="inline ml-1" /></span>
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

export function CrmTableView({ members, onSelect, isList = false }: TableProps) {
    return (
        <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg overflow-hidden shadow-sm animate-fade-in">
            <div className="overflow-x-auto">
                <table className="w-full text-left">
                    <thead className="bg-slate-50 dark:bg-black/20 border-b border-slate-200 dark:border-white/10 text-[10px] uppercase font-bold tracking-wide text-slate-400">
                        <tr>
                            <th className="px-4 py-2">Usuario</th>
                            <th className="px-4 py-2">Contacto</th>
                            {!isList && <th className="px-4 py-2">Estatus Espritual</th>}
                            <th className="px-4 py-2">Rol</th>
                            {!isList && <th className="px-4 py-2 text-right">Métricas</th>}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                        {members.map((m, idx) => (
                            <motion.tr 
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.01 }}
                                key={m.id} 
                                onClick={() => onSelect?.(m)}
                                className="group hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer transition-colors"
                            >
                                <td className="px-4 py-2">
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-md bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-900/40 dark:to-blue-800/20 text-blue-600 flex items-center justify-center font-bold text-sm group-hover:scale-110 transition-transform">
                                            {(m.first_name?.[0] || '')}{(m.last_name?.[0] || '')}
                                        </div>
                                        <div>
                                            <div className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">
                                                {m.first_name} {m.last_name}
                                            </div>
                                            <div className="text-[10px] font-bold text-slate-400">ID: #{m.id}</div>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-4 py-2">
                                    <div className="text-xs font-bold text-slate-600 dark:text-slate-300 flex items-center gap-1"><Mail size={12}/> {m.email || '—'}</div>
                                    <div className="text-xs text-slate-400 flex items-center gap-1 mt-1"><Phone size={12}/> {m.phone || '—'}</div>
                                </td>
                                {!isList && (
                                    <td className="px-4 py-2">
                                        <span className="px-2.5 py-1 bg-slate-100 dark:bg-white/10 rounded-lg text-[10px] font-bold uppercase text-slate-500 tracking-wider">
                                            {m.spiritual_status || 'Nuevo'}
                                        </span>
                                    </td>
                                )}
                                <td className="px-4 py-2">
                                    <span className={clsx(
                                        "px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider",
                                        m.church_role?.toLowerCase().includes('líder') 
                                            ? "bg-orange-100 text-orange-600 dark:bg-orange-900/30"
                                            : "bg-blue-50 text-blue-600 dark:bg-blue-900/30"
                                    )}>
                                        {m.church_role || 'Miembro'}
                                    </span>
                                </td>
                                {!isList && (
                                    <td className="px-4 py-2 text-right">
                                        <div className="flex items-center justify-end gap-3 text-xs font-bold text-slate-500">
                                            <div className="flex items-center gap-1 text-blue-600"><Heart size={14} fill="currentColor" /> {Math.round((m.spiritual_health || 0.8) * 100)}%</div>
                                        </div>
                                    </td>
                                )}
                            </motion.tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// 3. KANBAN / BOARD VIEW
// ----------------------------------------------------------------------
export function CrmKanbanView({ members, onSelect }: CrmViewProps) {
    const columns = useMemo(() => {
        const statuses = ['Nuevo', 'Consolidado', 'Activo', 'Líder', 'Inactivo'];
        const grouped = statuses.map(status => ({
            id: status,
            title: status,
            items: members.filter(m => (m.spiritual_status || 'Nuevo') === status)
        }));
        
        // Add "Otros" for statuses not in the list
        const others = members.filter(m => !statuses.includes(m.spiritual_status || 'Nuevo'));
        if (others.length > 0) {
            grouped.push({ id: 'Otros', title: 'Otros', items: others });
        }
        return grouped;
    }, [members]);

    return (
        <div className="flex gap-4 overflow-x-auto pb-8 snap-x snap-mandatory animate-fade-in" style={{ minHeight: '60vh' }}>
            {columns.map(col => (
                <div key={col.id} className="w-[320px] shrink-0 snap-start flex flex-col bg-slate-50/50 dark:bg-black/10 rounded-md border border-slate-200/50 dark:border-white/5 overflow-hidden">
                    <div className="p-4 border-b border-slate-200/50 dark:border-white/5 flex items-center justify-between bg-slate-100/50 dark:bg-white/5">
                        <h3 className="text-sm font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                            {col.title}
                        </h3>
                        <span className="px-2 py-0.5 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg text-xs font-bold text-slate-500">
                            {col.items.length}
                        </span>
                    </div>
                    
                    <div className="flex-1 p-3 space-y-3 overflow-y-auto">
                        {col.items.map(m => (
                            <div 
                                key={m.id} 
                                onClick={() => onSelect?.(m)}
                                className="p-4 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg shadow-sm hover:shadow-md hover:border-blue-500/50 cursor-pointer transition-all group"
                            >
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-xs font-bold text-slate-600 dark:text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                                        {(m.first_name?.[0] || '')}{(m.last_name?.[0] || '')}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-sm font-bold text-slate-900 dark:text-white truncate">
                                            {m.first_name} {m.last_name}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center justify-between mt-2">
                                    <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                                        {m.church_role || 'Miembro'}
                                    </span>
                                    <div className="flex gap-1 text-[10px] font-bold text-emerald-600">
                                        <Heart size={12} fill="currentColor" /> {Math.round((m.spiritual_health || 0.8) * 100)}%
                                    </div>
                                </div>
                            </div>
                        ))}
                        {col.items.length === 0 && (
                            <div className="h-24 flex items-center justify-center border-2 border-dashed border-slate-200 dark:border-white/5 rounded-lg text-xs font-bold text-slate-400 uppercase tracking-wide">
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
export function CrmCalendarView({ members, onSelect }: CrmViewProps) {
    // Generar un calendario mensual estático para la demo
    const days = Array.from({ length: 35 }, (_, i) => i + 1);
    
    return (
        <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md overflow-hidden animate-fade-in shadow-sm">
            <div className="p-4 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                <h3 className="text-sm font-bold tracking-tight"><Calendar size={20} className="inline mr-2 text-slate-400" /> Calendario de Registros</h3>
            </div>
            <div className="grid grid-cols-7 gap-px bg-slate-200 dark:bg-white/10">
                {['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'].map(d => (
                    <div key={d} className="bg-slate-50 dark:bg-[#1a1c1e] p-3 text-center text-[10px] font-bold uppercase tracking-wide text-slate-500">
                        {d}
                    </div>
                ))}
            </div>
            <div className="grid grid-cols-7 gap-px bg-slate-200 dark:bg-white/10">
                {days.map(d => {
                    const dayMembers = members.filter(m => {
                        const date = new Date(m.created_at);
                        return date.getDate() === (d > 31 ? d - 31 : d);
                    });

                    return (
                        <div key={d} className="bg-white dark:bg-[#1e1f21] min-h-12 p-2 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                            <span className="text-xs font-bold text-slate-400 mb-2 block">{d > 31 ? d - 31 : d}</span>
                            <div className="space-y-1">
                                {dayMembers.map(m => (
                                    <div 
                                        key={m.id} 
                                        onClick={() => onSelect?.(m)}
                                        className="text-[10px] font-bold px-2 py-1 bg-blue-50 text-blue-600 dark:bg-blue-900/30 rounded truncate cursor-pointer hover:bg-blue-100"
                                    >
                                        {m.first_name} {m.last_name}
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
export function CrmGanttView({ members }: CrmViewProps) {
    // Un timeline hiper simple de registros
    const sorted = [...members].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()).slice(0, 15);

    return (
        <div className="bg-white dark:bg-[#1e1f21] shadow-sm rounded-md border border-slate-200 dark:border-white/10 overflow-hidden animate-fade-in py-1.5 px-3">
            <h3 className="text-sm font-bold tracking-tight mb-3">Timeline de Integración (Últimos 15)</h3>
            <div className="space-y-3 relative before:absolute before:inset-0 before:ml-[11px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 dark:before:via-white/5 before:to-transparent">
                {sorted.map(m => (
                    <div key={m.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-6 h-6 rounded-full border-4 border-white dark:border-[#1e1f21] bg-blue-500 text-slate-500 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2"></div>
                        <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-lg border border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shadow-sm">
                            <div className="flex items-center justify-between mb-1">
                                <div className="font-bold text-sm text-slate-900 dark:text-white">{m.first_name} {m.last_name}</div>
                                <time className="text-[10px] font-bold text-slate-400 uppercase">{new Date(m.created_at).toLocaleDateString()}</time>
                            </div>
                            <div className="text-xs text-slate-500 font-bold">{m.church_role || 'Miembro'} ({m.spiritual_status || 'Nuevo'})</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

// Ensure MemberCard inside CRMClient.tsx is either removed or we keep it. 
// I'll export everything.
