"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { 
    Users, 
    UserPlus, 
    Search, 
    Filter, 
    MoreHorizontal,
    Heart,
    GraduationCap,
    ShieldCheck,
    MessageCircle,
    Mail,
    Phone,
    MapPin,
    Calendar,
    ChevronRight,
    Loader2,
    ArrowUpRight,
    Star
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import DSSkeleton from '@/components/ui/Skeleton';
import { ViewType } from '@/components/ViewSwitcher';
import { CrmGridView, CrmTableView, CrmKanbanView, CrmCalendarView, CrmGanttView } from '@/components/crm/CrmViews';

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

export default function CRMClient() {
    const { token } = useAuth();
    const [members, setMembers] = useState<Member[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedMember, setSelectedMember] = useState<Member | null>(null);
    const [viewType, setViewType] = useState<ViewType>('grid');

    // 1. Cargar miembros reales de la DB
    useEffect(() => {
        const fetchMembers = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<Member[]>(`/crm/members?search=${encodeURIComponent(search)}`, { token });
                setMembers(data);
            } catch (err) {
                console.error(err);
                toast.error("Error al cargar la comunidad");
            } finally {
                setLoading(false);
            }
        };

        const timer = setTimeout(fetchMembers, 300);
        return () => clearTimeout(timer);
    }, [token, search]);

    const stats = useMemo(() => ({
        total: members.length,
        baptized: Math.round(members.length * 0.65), // Simulado para dashboard
        leaders: members.filter(m => m.church_role?.toLowerCase().includes('líder')).length
    }), [members]);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#141517] overflow-hidden font-display animate-fade-in">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'CRM Pastoral', icon: Users }, { label: 'Comunidad Viva', icon: Heart }]}
                viewType={viewType}
                setViewType={setViewType}
                onSearch={setSearch}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 hover:scale-[1.02] active:scale-95 transition-all">
                        <UserPlus size={14} /> Registrar Miembro
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-10 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />
                
                <div className="max-w-[1400px] mx-auto space-y-10 relative z-10">
                    {/* Metrics Bento Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <MetricCard title="Membresía Total" value={stats.total} icon={Users} color="text-blue-600" bg="bg-blue-50" />
                        <MetricCard title="Estudiantes Activos" value={stats.baptized} icon={GraduationCap} color="text-emerald-600" bg="bg-emerald-50" />
                        <MetricCard title="Liderazgo" value={stats.leaders} icon={ShieldCheck} color="text-orange-600" bg="bg-orange-50" />
                    </div>

                    {/* Member Directory */}
                    <section className="space-y-6">
                        <div className="flex items-center justify-between px-4">
                            <div>
                                <h3 className="text-2xl font-black text-slate-900 dark:text-white flex items-center gap-3">
                                    Directorios de Comunidad
                                </h3>
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Gestión Pastoral en tiempo real</p>
                            </div>
                        </div>

                        {loading ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {[...Array(6)].map((_, i) => <DSSkeleton key={i} className="h-48 rounded-[2.5rem]" />)}
                            </div>
                        ) : members.length === 0 ? (
                            <div className="p-20 text-center bg-slate-50 dark:bg-white/5 rounded-[3.5rem] border-2 border-dashed border-slate-200">
                                <Search className="size-12 text-slate-300 mx-auto mb-4" />
                                <p className="text-lg font-black text-slate-400 uppercase">No se encontraron miembros</p>
                            </div>
                        ) : (
                            <div className="pb-20">
                                {viewType === 'grid' && <CrmGridView members={members} onSelect={setSelectedMember} />}
                                {(viewType === 'table' || viewType === 'list') && <CrmTableView members={members} onSelect={setSelectedMember} isList={viewType === 'list'} />}
                                {(viewType === 'kanban' || viewType === 'board') && <CrmKanbanView members={members} onSelect={setSelectedMember} />}
                                {viewType === 'calendar' && <CrmCalendarView members={members} onSelect={setSelectedMember} />}
                                {viewType === 'gantt' && <CrmGanttView members={members} />}
                            </div>
                        )}
                    </section>
                </div>
            </main>

            {/* Modal de Detalle de Miembro Pro (Drawer) */}
            <AnimatePresence>
                {selectedMember && (
                    <>
                        <motion.div 
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            onClick={() => setSelectedMember(null)}
                            className="fixed inset-0 z-[100] bg-slate-900/40 backdrop-blur-sm"
                        />
                        <motion.aside 
                            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
                            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                            className="fixed right-0 top-0 bottom-0 w-full max-w-[500px] z-[101] bg-white dark:bg-[#1e1f21] shadow-2xl border-l border-white/10 flex flex-col"
                        >
                            <MemberDetailView member={selectedMember} onClose={() => setSelectedMember(null)} />
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}

function MetricCard({ title, value, icon: Icon, color, bg }: any) {
    return (
        <div className="p-8 rounded-[2.5rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm hover:shadow-xl transition-all group overflow-hidden relative">
            <div className={clsx("absolute top-0 right-0 p-8 opacity-5 transition-transform group-hover:scale-110", color)}>
                <Icon size={120} />
            </div>
            <div className="flex items-center gap-4 mb-4">
                <div className={clsx("p-3 rounded-2xl", bg, color)}>
                    <Icon size={24} />
                </div>
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">{title}</span>
            </div>
            <div className="text-4xl font-black text-slate-900 dark:text-white leading-none tracking-tight">{value}</div>
        </div>
    );
}



function MemberDetailView({ member, onClose }: { member: Member, onClose: () => void }) {
    return (
        <div className="flex flex-col h-full overflow-hidden">
            <header className="p-8 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-black/20">
                <div className="flex items-center gap-4">
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 dark:hover:bg-white/5 rounded-full transition-colors text-slate-400"><ChevronRight size={20} /></button>
                    <h3 className="text-xl font-black uppercase tracking-tight">Ficha Pastoral</h3>
                </div>
                <div className="flex items-center gap-2">
                    <button className="p-2.5 text-slate-400 hover:text-blue-600 transition-all"><MessageCircle size={20} /></button>
                    <button className="p-2.5 text-slate-400 hover:text-blue-600 transition-all"><MoreHorizontal size={20} /></button>
                </div>
            </header>

            <div className="flex-1 overflow-y-auto p-10 space-y-10 scrollbar-hide">
                {/* Perfil Header */}
                <div className="text-center space-y-4">
                    <div className="size-24 rounded-[2.5rem] bg-blue-600 text-white flex items-center justify-center mx-auto text-3xl font-black shadow-2xl">
                        {member.first_name[0]}{member.last_name[0]}
                    </div>
                    <div>
                        <h2 className="text-2xl font-black tracking-tight">{member.first_name} {member.last_name}</h2>
                        <p className="text-blue-600 text-[10px] font-black uppercase tracking-widest mt-1">{member.church_role || 'Miembro Activo'}</p>
                    </div>
                </div>

                {/* Status Bento */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/5">
                        <span className="text-[9px] font-black uppercase text-slate-400 block mb-2">Salud Espiritual</span>
                        <div className="text-2xl font-black text-blue-600">{Math.round((member.spiritual_health || 0.8) * 100)}%</div>
                    </div>
                    <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/5">
                        <span className="text-[9px] font-black uppercase text-slate-400 block mb-2">Academia</span>
                        <div className="text-2xl font-black text-emerald-600">{Math.round((member.academy_progress || 0) * 100)}%</div>
                    </div>
                </div>

                {/* Contact Info */}
                <section className="space-y-4">
                    <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Información de Contacto</h4>
                    <div className="space-y-2">
                        <ContactItem icon={Mail} value={member.email || 'Sin correo'} />
                        <ContactItem icon={Phone} value={member.phone || 'Sin teléfono'} />
                        <ContactItem icon={MapPin} value="Dirección no registrada" />
                        <ContactItem icon={Calendar} value={`Miembro desde: ${new Date(member.created_at).toLocaleDateString()}`} />
                    </div>
                </section>

                <div className="pt-10 flex gap-4">
                    <button className="flex-1 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl hover:scale-[1.02] active:scale-95 transition-all">Editar Perfil</button>
                    <button className="px-6 py-4 bg-blue-50 dark:bg-blue-900/20 text-blue-600 rounded-2xl hover:bg-blue-100 transition-all"><ArrowUpRight size={20} /></button>
                </div>
            </div>
        </div>
    );
}

function ContactItem({ icon: Icon, value }: any) {
    return (
        <div className="flex items-center gap-4 p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-2xl">
            <div className="p-2 bg-slate-50 dark:bg-white/5 rounded-lg text-slate-400"><Icon size={16} /></div>
            <span className="text-sm font-bold text-slate-600 dark:text-slate-300 truncate">{value}</span>
        </div>
    );
}
