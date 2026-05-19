"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { 
    Users, 
    UserPlus, 
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
    Sparkles,
    Search,
    User,
    Users as FamilyIcon
} from 'lucide-react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import DSSkeleton from '@/components/ui/Skeleton';
import { ViewType } from '@/components/ViewSwitcher';
import { CrmGridView, CrmTableView, CrmKanbanView, CrmCalendarView, CrmGanttView } from '@/components/crm/CrmViews';
import RightPanel from '@/components/ui/RightPanel';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { CrmAnalyticsSummary, CrmMember } from './types';

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

interface CrmClientProps {
    initialMembers?: CrmMember[];
}

export default function CRMClient({ initialMembers = [] }: CrmClientProps) {
    const { token } = useAuth();
    const router = useRouter();
    const { openLayer, closeLayer, setRightMode, layers } = useSidebarLayers();
    const [members, setMembers] = useState<Member[]>(() => initialMembers as unknown as Member[]);
    const [loading, setLoading] = useState(true);
    const [analytics, setAnalytics] = useState<CrmAnalyticsSummary | null>(null);
    const [search, setSearch] = useState('');
    const [selectedMember, setSelectedMember] = useState<Member | null>(null);
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        if (!layers?.RIGHT && selectedMember) {
            setSelectedMember(null);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [layers?.RIGHT]);

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

    useEffect(() => {
        if (!token) return;

        let alive = true;
        const fetchAnalytics = async () => {
            try {
                const data = await apiFetch<CrmAnalyticsSummary>('/crm/analytics', {
                    token,
                    cache: 'no-store',
                });
                if (alive) setAnalytics(data);
            } catch (err) {
                console.error(err);
            }
        };

        fetchAnalytics();
        return () => {
            alive = false;
        };
    }, [token]);

    const stats = useMemo(() => {
        const activeMembersFromRows = members.filter(member =>
            ['activo', 'active', 'miembro activo'].includes(member.spiritual_status?.toLowerCase() ?? '')
        ).length;

        return {
            total: analytics?.total_members ?? members.length,
            active: analytics?.active_members ?? activeMembersFromRows,
            leaders: members.filter(m => m.church_role?.toLowerCase().includes('líder')).length,
        };
    }, [analytics, members]);

    return (
        <WorkspaceLayout
            breadcrumbs={[{ label: 'Consolidación', icon: Users }, { label: 'Comunidad Viva', icon: Heart }]}
            viewType={viewType}
            setViewType={setViewType}
            onSearch={setSearch}
            rightActions={
                <SplitDropdownButton
                    mainLabel="Nuevo"
                    icon={UserPlus}
                    onMainClick={() => router.push('/crm/members')}
                    options={[
                        { id: 'member', label: 'Miembro', icon: User, onClick: () => router.push('/crm/members') },
                        { id: 'family', label: 'Familia', icon: FamilyIcon, onClick: () => router.push('/crm/members') },
                        { id: 'appointment', label: 'Cita', icon: Calendar, onClick: () => router.push('/crm/counseling') },
                        { id: 'call', label: 'Llamada', icon: Phone, onClick: () => router.push('/crm/pipeline') },
                        { id: 'mail', label: 'Email', icon: Mail, onClick: () => router.push('/crm/pipeline') },
                        { id: 'sms', label: 'SMS', icon: MessageCircle, onClick: () => router.push('/crm/pipeline') }
                    ]}
                />
            }
        >
            <main className="flex-1 overflow-y-auto scrollbar-thin p-10 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />
                
                <div className="max-w-[1400px] mx-auto space-y-10 relative z-10">
                    {/* Metrics Bento Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <MetricCard title="Membresía Total" value={stats.total} icon={Users} color="text-blue-600" bg="bg-blue-50 dark:bg-blue-500/10" />
                        <MetricCard title="Miembros Activos" value={stats.active} icon={GraduationCap} color="text-emerald-600" bg="bg-emerald-50 dark:bg-emerald-500/10" />
                        <MetricCard title="Liderazgo" value={stats.leaders} icon={ShieldCheck} color="text-orange-600" bg="bg-orange-50 dark:bg-orange-500/10" />
                    </div>

                    {/* Member Directory */}
                    <section className="space-y-5">
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-[18px] font-bold text-slate-900 dark:text-white tracking-tight">Directorio de Consolidación</h3>
                                <p className="text-[11px] text-slate-400 font-medium mt-0.5">Gestión de miembros en tiempo real</p>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 bg-slate-100 dark:bg-white/5 px-3 py-1.5 rounded-lg">
                                {members.length} miembros
                            </span>
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
                                {viewType === 'grid' && <CrmGridView members={members} onSelect={(m) => { setSelectedMember(m); setRightMode('overlay'); openLayer('RIGHT'); }} />}
                                {(viewType === 'table' || viewType === 'list') && <CrmTableView members={members} onSelect={(m) => { setSelectedMember(m); setRightMode('overlay'); openLayer('RIGHT'); }} isList={viewType === 'list'} />}
                                {(viewType === 'kanban' || viewType === 'board') && <CrmKanbanView members={members} onSelect={(m) => { setSelectedMember(m); setRightMode('overlay'); openLayer('RIGHT'); }} />}
                                {viewType === 'calendar' && <CrmCalendarView members={members} onSelect={(m) => { setSelectedMember(m); setRightMode('overlay'); openLayer('RIGHT'); }} />}
                                {viewType === 'gantt' && <CrmGanttView members={members} />}
                            </div>
                        )}
                    </section>
                </div>
            </main>

            {/* Panel lateral sin modales usando RightPanel (Estándar Clean Productivity) */}
            {selectedMember && (
                <RightPanel title="Ficha de Consolidación" width={500}>
                    <MemberDetailView member={selectedMember} onClose={() => {
                        setSelectedMember(null);
                        closeLayer('RIGHT');
                    }} />
                </RightPanel>
            )}
        </WorkspaceLayout>
    );
}

function MetricCard({ title, value, icon: Icon, color, bg }: any) {
    return (
        <div className="relative p-6 rounded-2xl bg-white dark:bg-[#1e2025] border border-slate-100 dark:border-white/[0.06] shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 group cursor-pointer overflow-hidden">
            {/* Subtle gradient glow top-right */}
            <div className={`absolute -top-6 -right-6 size-24 rounded-full blur-2xl opacity-20 group-hover:opacity-40 transition-opacity ${bg}`} />
            <div className="flex items-start justify-between mb-5 relative z-10">
                <div className={`inline-flex items-center justify-center size-11 rounded-xl ${bg} ${color} shadow-sm`}>
                    <Icon size={20} />
                </div>
                <span className={`text-[10px] font-black px-2 py-1 rounded-lg ${bg} ${color} opacity-0 group-hover:opacity-100 transition-opacity`}>
                    Ver todo
                </span>
            </div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 mb-1 relative z-10">{title}</p>
            <div className="text-4xl font-black text-slate-900 dark:text-white leading-none tracking-tight relative z-10">{value}</div>
        </div>
    );
}



function MemberDetailView({ member, onClose }: { member: Member, onClose: () => void }) {
    const { token } = useAuth();
    const [aiInsight, setAiInsight] = useState<string | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [consolidationProfile, setConsolidationProfile] = useState<{
        member: {
            id: number;
            first_name: string;
            last_name: string;
            church_role: string | null;
            spiritual_status: string | null;
        };
        positions: Array<{
            id: number;
            position_name: string | null;
            category: string | null;
            start_date: string | null;
            end_date: string | null;
            is_active: boolean;
            notes: string | null;
        }>;
        cases: Array<{
            id: number;
            stage: string;
            status: string;
            source: string | null;
            last_contact_at: string | null;
            next_contact_at: string | null;
            assignments_count: number;
            interactions_count: number;
            open_tasks_count: number;
        }>;
    } | null>(null);
    const [loadingProfile, setLoadingProfile] = useState(false);
    const [attendanceHistory, setAttendanceHistory] = useState<{
        total_records: number;
        history: Array<{
            event_id: number;
            event_name: string | null;
            event_date: string | null;
            session_date: string | null;
            status: string;
            check_in_at: string | null;
        }>;
    } | null>(null);
    const [loadingAttendance, setLoadingAttendance] = useState(false);

    useEffect(() => {
        if (!token) return;
        let alive = true;

        const loadProfile = async () => {
            setLoadingProfile(true);
            try {
                const data = await apiFetch<any>(`/crm/members/${member.id}/consolidation`, { token, cache: 'no-store' });
                if (alive) setConsolidationProfile(data);
            } catch {
                if (alive) setConsolidationProfile(null);
            } finally {
                if (alive) setLoadingProfile(false);
            }
        };

        const loadAttendance = async () => {
            setLoadingAttendance(true);
            try {
                const data = await apiFetch<any>(`/evangelism/members/${member.id}/attendance-history`, { token, cache: 'no-store' });
                if (alive) setAttendanceHistory(data);
            } catch {
                if (alive) setAttendanceHistory(null);
            } finally {
                if (alive) setLoadingAttendance(false);
            }
        };

        loadProfile();
        loadAttendance();

        return () => {
            alive = false;
        };
    }, [member.id, token]);

    const handleAiAnalysis = async () => {
        setIsAnalyzing(true);
        try {
            const context = `Miembro: ${member.first_name} ${member.last_name}. Rol: ${member.church_role || 'Miembro'}. Salud Espiritual: ${Math.round((member.spiritual_health || 0.8) * 100)}%. Progreso Academia: ${Math.round((member.academy_progress || 0) * 100)}%.`;
            const prompt = `Actúa como un pastor mentor. Basado en estos datos, escribe un breve y alentador diagnóstico pastoral (máximo 3 líneas) y sugiere un paso de acción concreto para su crecimiento.`;
            
            const data = await apiFetch<{response: string}>('/system/ai/generate', {
                method: 'POST',
                token,
                body: { prompt, context }
            });
            setAiInsight(data.response);
            toast.success("Diagnóstico pastoral completado");
        } catch (err) {
            toast.error("Error al conectar con Optimus Brain");
        } finally {
            setIsAnalyzing(false);
        }
    };

    return (
        <div className="flex flex-col h-full overflow-hidden">
            <header className="p-8 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-black/20 shrink-0">
                <div className="flex items-center gap-4">
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 dark:hover:bg-white/5 rounded-full transition-colors text-slate-400"><ChevronRight size={20} /></button>
                    <h3 className="text-[12px] font-black uppercase tracking-[0.2em] text-slate-800 dark:text-white">Ficha de Consolidación</h3>
                </div>
                <div className="flex items-center gap-2">
                    <button className="p-2.5 text-slate-400 hover:text-blue-600 transition-all"><MessageCircle size={18} /></button>
                    <button className="p-2.5 text-slate-400 hover:text-blue-600 transition-all"><MoreHorizontal size={18} /></button>
                </div>
            </header>

            <div className="flex-1 overflow-y-auto p-10 space-y-10 scrollbar-hide">
                {/* Perfil Header */}
                <div className="text-center space-y-4">
                    <div className="size-24 rounded-[2.5rem] bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center mx-auto text-3xl font-black shadow-xl shadow-blue-500/20">
                        {member.first_name[0]}{member.last_name[0]}
                    </div>
                    <div>
                        <h2 className="text-3xl font-black tracking-tight leading-none mb-2">{member.first_name} {member.last_name}</h2>
                        <span className="px-3 py-1 bg-slate-100 dark:bg-white/5 rounded-lg text-blue-600 text-[10px] font-black uppercase tracking-widest">{member.church_role || 'Miembro Activo'}</span>
                    </div>
                </div>

                {/* Optimus Brain Action */}
                <div className="relative group cursor-pointer" onClick={handleAiAnalysis}>
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-[2rem] blur opacity-10 group-hover:opacity-30 transition-opacity" />
                    <div className="relative p-6 bg-white dark:bg-[#1e1f21] rounded-[2rem] border border-blue-500/20 shadow-sm flex flex-col items-center text-center gap-3">
                        {isAnalyzing ? (
                            <Loader2 className="size-8 text-blue-600 animate-spin" />
                        ) : (
                            <div className="size-12 rounded-2xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600">
                                <Sparkles size={24} />
                            </div>
                        )}
                        <div>
                            <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900 dark:text-white mb-1">Optimus Consolidación</h4>
                            <p className="text-xs text-slate-500 font-medium">Haz clic para generar un análisis espiritual con IA basado en su métrica.</p>
                        </div>
                        
                        <AnimatePresence>
                            {aiInsight && (
                                <motion.div 
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    className="mt-4 pt-4 border-t border-slate-100 dark:border-white/5 text-left w-full"
                                >
                                    <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed font-medium italic">
                                        &quot;{aiInsight}&quot;
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>

                {/* Status Bento */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-[2rem] border border-slate-100 dark:border-white/5 hover:shadow-md transition-all">
                        <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 block mb-2">Salud Espiritual</span>
                        <div className="text-3xl font-black text-blue-600">{Math.round((member.spiritual_health || 0.8) * 100)}%</div>
                    </div>
                    <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-[2rem] border border-slate-100 dark:border-white/5 hover:shadow-md transition-all">
                        <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 block mb-2">Academia</span>
                        <div className="text-3xl font-black text-emerald-600">{Math.round((member.academy_progress || 0) * 100)}%</div>
                    </div>
                </div>

                {/* Contact Info */}
                <section className="space-y-4">
                    <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Directorio de Contacto</h4>
                    <div className="space-y-2">
                        <ContactItem icon={Mail} value={member.email || 'Sin correo'} />
                        <ContactItem icon={Phone} value={member.phone || 'Sin teléfono'} />
                        <ContactItem icon={MapPin} value="Dirección no registrada" />
                        <ContactItem icon={Calendar} value={`Alta: ${new Date(member.created_at).toLocaleDateString()}`} />
                    </div>
                </section>

                <section className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Consolidación</h4>
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                            {loadingProfile ? 'Cargando...' : `${consolidationProfile?.cases?.length ?? 0} casos`}
                        </span>
                    </div>
                    <div className="space-y-3">
                        {loadingProfile ? (
                            <div className="rounded-2xl border border-slate-100 dark:border-white/5 p-4 text-sm text-slate-400">
                                Cargando perfil...
                            </div>
                        ) : (
                            <>
                                <div className="rounded-2xl border border-slate-100 dark:border-white/5 bg-white dark:bg-white/5 p-4">
                                    <div className="flex items-center justify-between mb-3">
                                        <h5 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Cargos actuales</h5>
                                        <span className="text-[10px] font-black uppercase tracking-widest text-blue-600">{consolidationProfile?.positions?.filter(p => p.is_active).length ?? 0}</span>
                                    </div>
                                    <div className="space-y-2">
                                        {consolidationProfile?.positions?.length ? (
                                            consolidationProfile.positions.map((row) => (
                                                <div key={row.id} className="rounded-xl bg-slate-50 dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 px-3 py-2">
                                                    <div className="flex items-center justify-between gap-3">
                                                        <div className="min-w-0">
                                                            <p className="text-sm font-bold text-slate-800 dark:text-white truncate">{row.position_name || 'Cargo'}</p>
                                                            <p className="text-[10px] uppercase font-black tracking-widest text-slate-400">{row.category || 'Sin categoría'}</p>
                                                        </div>
                                                        <span className={`px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest ${row.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' : 'bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-slate-400'}`}>
                                                            {row.is_active ? 'Activo' : 'Histórico'}
                                                        </span>
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <p className="text-sm text-slate-400">Sin cargos registrados.</p>
                                        )}
                                    </div>
                                </div>

                                <div className="rounded-2xl border border-slate-100 dark:border-white/5 bg-white dark:bg-white/5 p-4">
                                    <div className="flex items-center justify-between mb-3">
                                        <h5 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Casos de consolidación</h5>
                                        <span className="text-[10px] font-black uppercase tracking-widest text-blue-600">{consolidationProfile?.cases?.length ?? 0}</span>
                                    </div>
                                    <div className="space-y-2">
                                        {consolidationProfile?.cases?.length ? (
                                            consolidationProfile.cases.map((row) => (
                                                <div key={row.id} className="rounded-xl bg-slate-50 dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 px-3 py-2">
                                                    <div className="flex items-start justify-between gap-3">
                                                        <div className="min-w-0">
                                                            <p className="text-sm font-bold text-slate-800 dark:text-white truncate">Etapa {row.stage}</p>
                                                            <p className="text-[10px] uppercase font-black tracking-widest text-slate-400">{row.source || 'Sin origen'}</p>
                                                        </div>
                                                        <span className={`px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest ${row.status === 'active' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' : 'bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-slate-400'}`}>
                                                            {row.status}
                                                        </span>
                                                    </div>
                                                    <div className="mt-2 flex items-center gap-3 text-[10px] font-black uppercase tracking-widest text-slate-400">
                                                        <span>{row.assignments_count} asignaciones</span>
                                                        <span>{row.interactions_count} interacciones</span>
                                                        <span>{row.open_tasks_count} tareas</span>
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <p className="text-sm text-slate-400">Sin casos abiertos.</p>
                                        )}
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </section>

                <section className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Asistencia a Eventos</h4>
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                            {loadingAttendance ? 'Cargando...' : `${attendanceHistory?.total_records ?? 0} registros`}
                        </span>
                    </div>
                    <div className="space-y-2">
                        {loadingAttendance ? (
                            <div className="rounded-2xl border border-slate-100 dark:border-white/5 p-4 text-sm text-slate-400">
                                Cargando historial...
                            </div>
                        ) : attendanceHistory?.history?.length ? (
                            attendanceHistory.history.slice(0, 6).map((row) => (
                                <div key={`${row.event_id}-${row.session_date}`} className="rounded-2xl border border-slate-100 dark:border-white/5 bg-white dark:bg-white/5 p-4">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <p className="text-sm font-bold text-slate-800 dark:text-white truncate">{row.event_name || 'Evento'}</p>
                                            <p className="text-[11px] text-slate-500 mt-0.5">
                                                {row.event_date ? new Date(row.event_date).toLocaleDateString() : 'Sin fecha'} Â· {row.status}
                                            </p>
                                        </div>
                                        <span className={`px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest ${row.status === 'present' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' : 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400'}`}>
                                            {row.status}
                                        </span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="rounded-2xl border border-dashed border-slate-200 dark:border-white/10 p-4 text-sm text-slate-400">
                                Sin asistencia registrada.
                            </div>
                        )}
                    </div>
                </section>
            </div>
            
            <footer className="p-6 border-t border-slate-100 dark:border-white/5 flex gap-4 bg-white dark:bg-[#1e1f21] shrink-0">
                <button className="flex-1 py-4 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all">Editar Perfil</button>
                <button className="px-8 py-4 bg-blue-600 text-white rounded-2xl shadow-xl shadow-blue-500/20 hover:scale-[1.02] transition-all"><ArrowUpRight size={20} /></button>
            </footer>
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


