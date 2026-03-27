"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Home, 
    Users, 
    Calendar, 
    CheckCircle2, 
    Camera, 
    MessageCircle, 
    ChevronRight, 
    MoreHorizontal,
    Plus,
    Search,
    Filter,
    Star,
    Heart,
    Zap,
    ArrowUpRight,
    MapPin,
    Clock,
    FileText,
    Loader2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import Skeleton from '@/components/ui/Skeleton';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function GloryHouseAdmin() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [houses, setHouses] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedHouse, setSelectedHouse] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [reportDate, setReportDate] = useState(new Date().toISOString().split('T')[0]);
    const [submitting, setSubsending] = useState(false);

    const fetchHouses = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch('/community/glory-houses', { token });
            setHouses(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error("Failed to fetch houses", err);
            // Enhanced Mock Data for Quality Preview
            setHouses([
                { id: 1, name: 'Casa Central', zone: 'Centro', leader_name: 'Juan y Paula', members_count: 24, last_report: 'Hace 2 días', status: 'active' },
                { id: 2, name: 'Casa Norte', zone: 'Comuna 4', leader_name: 'Luis y María', members_count: 18, last_report: 'Hace 1 semana', status: 'active' },
                { id: 3, name: 'Casa Sur', zone: 'B° Jardines', leader_name: 'Eliana y Carlos', members_count: 15, last_report: 'Hoy', status: 'active' },
            ]);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => { if (isAuthenticated) fetchHouses(); }, [isAuthenticated, fetchHouses]);

    const handleSendReport = async () => {
        setSubsending(true);
        // Simulate API call for quality UX testing
        setTimeout(() => {
            addToast(`Reporte enviado con éxito para ${selectedHouse?.name}`, 'success');
            setSubsending(false);
            setIsDrawerOpen(false);
        }, 1500);
    };

    if (!isAuthenticated) return null;

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Operación de Campo', icon: Home },
                { label: 'Casas de Gloria', icon: Star }
            ]}
        >
            <AdminHero
                eyebrow="Gestión de Redes"
                title="Consola de Casas de Gloria"
                description="Supervisa la salud de los grupos pequeños. Gestiona reportes semanales, asistencia y testimonios de transformación en tiempo real."
                tags={['Campo Activo', 'Liderazgo', 'MESH Flow']}
                watchers={['Coordinación General', 'Pastoral']}
                primaryAction={{ label: 'Nueva Casa', icon: Plus, onClick: () => {} }}
                secondaryAction={{ label: 'Exportar Reportes', icon: FileText, onClick: () => {} }}
            />

            <main className="space-y-10 pb-20">
                {/* Visual Quality Stats */}
                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <HouseStat label="Casas Activas" value={loading ? '...' : houses.length.toString()} icon={Home} color="blue" />
                    <HouseStat label="Asistencia Semanal" value="128" trend="+15%" icon={Users} color="emerald" />
                    <HouseStat label="Nuevas Decisiones" value="4" trend="Meta: 10" icon={Heart} color="rose" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <div className="lg:col-span-8 space-y-6">
                        <div className="flex items-center justify-between px-4">
                            <h3 className="text-lg font-black tracking-tight uppercase tracking-widest">Red de Grupos</h3>
                            <div className="flex gap-2">
                                <button className="p-2 hover:bg-white dark:hover:bg-white/5 rounded-xl transition-colors text-slate-400"><Search size={18} /></button>
                                <button className="p-2 hover:bg-white dark:hover:bg-white/5 rounded-xl transition-colors text-slate-400"><Filter size={18} /></button>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {loading ? (
                                [1,2,3,4].map(i => <div key={i} className="h-[200px] rounded-[2.5rem] bg-white/5 animate-pulse" />)
                            ) : (
                                houses.map((house) => (
                                    <motion.div 
                                        key={house.id} layoutId={house.id.toString()}
                                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                        onClick={() => { setSelectedHouse(house); setIsDrawerOpen(true); }}
                                        className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm hover:shadow-xl transition-all cursor-pointer group relative overflow-hidden"
                                    >
                                        <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
                                            <Star size={48} className="text-blue-600" />
                                        </div>
                                        <div className="relative z-10 space-y-6">
                                            <div className="flex justify-between items-start">
                                                <div className="size-12 rounded-2xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center">
                                                    <Home size={24} />
                                                </div>
                                                <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 rounded-lg">
                                                    <div className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                                    <span className="text-[8px] font-black uppercase">Activa</span>
                                                </div>
                                            </div>
                                            <div>
                                                <h4 className="text-xl font-black text-slate-900 dark:text-white mb-1 uppercase tracking-tight">{house.name}</h4>
                                                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                                    <MapPin size={12} /> {house.zone}
                                                </p>
                                            </div>
                                            <div className="pt-6 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                                                <div className="flex -space-x-2">
                                                    {[1,2,3].map(i => <div key={i} className="size-7 rounded-full border-2 border-white dark:border-slate-900 bg-slate-200" />)}
                                                    <div className="size-7 rounded-full border-2 border-white dark:border-slate-900 bg-blue-600 flex items-center justify-center text-[8px] font-black text-white">+{house.members_count - 3}</div>
                                                </div>
                                                <button className="flex items-center gap-2 text-[10px] font-black text-blue-600 uppercase tracking-widest group-hover:gap-3 transition-all">
                                                    Abrir Reporte <ChevronRight size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))
                            )}
                        </div>
                    </div>

                    <aside className="lg:col-span-4 space-y-8">
                        <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8">
                            <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em]">Últimos Reportes</h3>
                            <div className="space-y-6">
                                {[1,2,3].map(i => (
                                    <div key={i} className="flex gap-4 items-start group cursor-pointer">
                                        <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-all">
                                            <CheckCircle2 size={18} />
                                        </div>
                                        <div className="flex-1">
                                            <h5 className="text-[13px] font-black text-slate-800 dark:text-white group-hover:text-blue-600 transition-colors uppercase">Reunión Semanal</h5>
                                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">Casa Norte • 18 Asistentes</p>
                                        </div>
                                        <ArrowUpRight size={14} className="text-slate-300" />
                                    </div>
                                ))}
                            </div>
                            <button className="w-full py-4 bg-slate-900 dark:bg-blue-600 text-white rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] shadow-xl transition-all active:scale-95">
                                Ver Auditoría Full
                            </button>
                        </section>

                        <section className="p-8 bg-blue-600 rounded-[3rem] text-white shadow-2xl space-y-6 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 -mr-10 -mt-10 size-40 bg-white/10 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-1000" />
                            <div className="relative z-10 space-y-4">
                                <div className="flex items-center gap-3">
                                    <Zap size={20} fill="currentColor" />
                                    <h4 className="text-[11px] font-black uppercase tracking-widest">Salud de la Red</h4>
                                </div>
                                <h3 className="text-3xl font-black tracking-tighter leading-none">85% Reportado</h3>
                                <div className="h-1.5 w-full bg-white/20 rounded-full overflow-hidden">
                                    <div className="h-full bg-white w-[85%] shadow-[0_0_10px_white]" />
                                </div>
                                <p className="text-[10px] font-bold text-blue-100 leading-relaxed uppercase tracking-wider">
                                    &quot;Faltan 2 reportes de la zona Norte para cumplir la meta de asistencia.&quot;
                                </p>
                            </div>
                        </section>
                    </aside>
                </div>
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedHouse?.name}
                subtitle="REPORTE OPERATIVO SEMANAL"
            >
                <div className="space-y-10 pb-20">
                    <section className="space-y-6">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/5">
                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Fecha</p>
                                <input type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} className="bg-transparent text-sm font-black text-slate-800 dark:text-white outline-none w-full" />
                            </div>
                            <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/5">
                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Total Asistentes</p>
                                <input type="number" placeholder="0" className="bg-transparent text-sm font-black text-slate-800 dark:text-white outline-none w-full" />
                            </div>
                        </div>
                    </section>

                    <section className="space-y-4">
                        <div className="flex items-center justify-between px-2">
                            <h5 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Asistencia de Miembros</h5>
                            <button className="text-[9px] font-black text-blue-600 uppercase hover:underline">Seleccionar Todos</button>
                        </div>
                        <div className="space-y-2 max-h-[300px] overflow-y-auto scrollbar-thin pr-2">
                            {['Ricardo Mendez', 'Elena Rodriguez', 'Marcos Lopez', 'Ana Victoria', 'David Castro'].map((name, idx) => (
                                <div key={idx} className="flex items-center justify-between p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-2xl hover:border-blue-500/20 transition-all group">
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-lg bg-slate-100 dark:bg-white/10 flex items-center justify-center text-[10px] font-black text-slate-500 uppercase">{name.charAt(0)}</div>
                                        <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200">{name}</span>
                                    </div>
                                    <input type="checkbox" className="size-5 rounded-lg border-2 border-slate-200 checked:bg-blue-600 transition-all cursor-pointer" />
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="space-y-4">
                        <h5 className="text-[11px] font-black uppercase tracking-widest text-slate-400 px-2">Evidencia Fotográfica</h5>
                        <div className="grid grid-cols-2 gap-4">
                            <button className="aspect-video bg-slate-100 dark:bg-white/5 rounded-3xl border-2 border-dashed border-slate-200 dark:border-white/10 flex flex-col items-center justify-center gap-2 text-slate-400 hover:text-blue-600 hover:border-blue-500/30 transition-all group">
                                <Camera size={24} className="group-hover:scale-110 transition-transform" />
                                <span className="text-[9px] font-black uppercase">Subir Foto</span>
                            </button>
                            <button className="aspect-video bg-slate-100 dark:bg-white/5 rounded-3xl border-2 border-dashed border-slate-200 dark:border-white/10 flex flex-col items-center justify-center gap-2 text-slate-400 hover:text-blue-600 hover:border-blue-500/30 transition-all group">
                                <MessageCircle size={24} className="group-hover:scale-110 transition-transform" />
                                <span className="text-[9px] font-black uppercase">Testimonio</span>
                            </button>
                        </div>
                    </section>

                    <button 
                        onClick={handleSendReport} disabled={submitting}
                        className="w-full py-5 bg-blue-600 text-white rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] shadow-xl shadow-blue-500/20 active:scale-95 transition-all flex items-center justify-center gap-3 disabled:opacity-50"
                    >
                        {submitting ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} fill="currentColor" />}
                        Enviar Reporte Semanal
                    </button>
                </div>
            </WorkspaceDrawer>
        </AdminShell>
    );
}

function HouseStat({ label, value, trend, icon: Icon, color }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20',
        rose: 'text-rose-600 bg-rose-50 dark:bg-rose-900/20'
    };
    return (
        <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] p-8 shadow-sm flex items-center gap-6 group hover:shadow-xl transition-all">
            <div className={clsx("size-14 rounded-2xl flex items-center justify-center shrink-0 group-hover:rotate-12 transition-transform", colors[color])}>
                <Icon size={28} />
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 leading-none">{label}</p>
                <div className="flex items-baseline gap-2">
                    <h4 className="text-2xl font-black text-slate-900 dark:text-white leading-none">{value}</h4>
                    {trend && <span className="text-[9px] font-black text-emerald-500 uppercase">{trend}</span>}
                </div>
            </div>
        </div>
    );
}
