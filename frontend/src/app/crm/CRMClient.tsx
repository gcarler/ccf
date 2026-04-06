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
    Star,
    Sparkles,
    User,
    Users as FamilyIcon
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import DSSkeleton from '@/components/ui/Skeleton';
import { ViewType } from '@/components/ViewSwitcher';
import { CrmGridView, CrmTableView, CrmKanbanView, CrmCalendarView, CrmGanttView } from '@/components/crm/CrmViews';
import RightPanel from '@/components/ui/RightPanel';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

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
    const router = useRouter();
    const { openLayer, closeLayer, setRightMode, layers } = useSidebarLayers();
    const [members, setMembers] = useState<Member[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedMember, setSelectedMember] = useState<Member | null>(null);
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        if (!layers?.RIGHT && selectedMember) {
            setSelectedMember(null);
        }
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
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-10 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />
                
                <div className="max-w-[1400px] mx-auto space-y-10 relative z-10">
                    {/* Metrics Bento Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <MetricCard title="Membresía Total" value={stats.total} icon={Users} color="text-blue-600" bg="bg-blue-50 dark:bg-blue-500/10" />
                        <MetricCard title="Estudiantes Activos" value={stats.baptized} icon={GraduationCap} color="text-emerald-600" bg="bg-emerald-50 dark:bg-emerald-500/10" />
                        <MetricCard title="Liderazgo" value={stats.leaders} icon={ShieldCheck} color="text-orange-600" bg="bg-orange-50 dark:bg-orange-500/10" />
                    </div>

                    {/* Member Directory */}
                    <section className="space-y-5">
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-[18px] font-bold text-slate-900 dark:text-white tracking-tight">Directorio Pastoral</h3>
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
                <RightPanel title="Ficha Pastoral" width={500}>
                    <MemberDetailView member={selectedMember} onClose={() => {
                        setSelectedMember(null);
                        closeLayer('RIGHT');
                    }} />
                </RightPanel>
            )}
        </div>
    );
}

function MetricCard({ title, value, icon: Icon, color, bg, accent }: any) {
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
                    <h3 className="text-[12px] font-black uppercase tracking-[0.2em] text-slate-800 dark:text-white">Ficha Pastoral</h3>
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
                            <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-900 dark:text-white mb-1">Optimus Pastoral</h4>
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
                                        "{aiInsight}"
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
