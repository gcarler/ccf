"use client";

import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { 
    Award, 
    Church, 
    School, 
    Lock, 
    ChevronRight, 
    BookOpen, 
    History,
    TrendingUp,
    CheckCircle2,
    Settings,
    ShieldCheck
} from 'lucide-react';

export default function StudentProfilePage() {
    const { user } = useAuth();

    const badges = [
        { name: "Primer Curso", desc: "Completado", icon: Award, color: "from-yellow-300 to-amber-600", active: true },
        { name: "Intercesor", desc: "Activo", icon: Church, color: "from-blue-300 to-blue-600", active: true },
        { name: "Estudiante", desc: "Destacado", icon: School, color: "from-slate-200 to-slate-400", active: true },
        { name: "Misionero", desc: "Global", icon: Lock, color: "bg-slate-200", active: false },
    ];

    return (
        <div className="space-y-10 animate-in fade-in duration-700 max-w-5xl mx-auto">
            
            {/* Header Profile Section */}
            <section className="relative overflow-hidden rounded-[3.5rem] bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-white/5 p-10 shadow-2xl">
                <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
                
                <div className="flex flex-col md:flex-row items-center gap-10 relative z-10">
                    <div className="relative">
                        <div className="absolute inset-0 rounded-full border-4 border-primary animate-pulse opacity-30 blur-lg"></div>
                        <div className="size-40 rounded-full border-4 border-white dark:border-slate-800 shadow-2xl overflow-hidden relative">
                            <img 
                                src={`https://ui-avatars.com/api/?name=${user?.username || 'U'}&background=1973f0&color=fff&size=256`} 
                                alt="Profile" 
                                className="w-full h-full object-cover"
                            />
                        </div>
                        <div className="absolute bottom-2 right-2 size-8 bg-primary text-white rounded-full flex items-center justify-center border-4 border-white dark:border-slate-800 shadow-lg">
                            <ShieldCheck size={16} />
                        </div>
                    </div>

                    <div className="text-center md:text-left space-y-4">
                        <div>
                            <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight mb-1">{user?.username || 'Juan Pérez'}</h1>
                            <p className="text-primary font-bold uppercase tracking-widest text-xs">Estudiante de Teología • 3er Semestre</p>
                        </div>
                        <div className="flex flex-wrap justify-center md:justify-start gap-3">
                            <div className="px-4 py-2 bg-slate-100 dark:bg-white/5 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-500">ID: 2024-0012</div>
                            <div className="px-4 py-2 bg-emerald-500/10 text-emerald-500 rounded-xl text-[10px] font-black uppercase tracking-widest border border-emerald-500/20 flex items-center gap-2">
                                <CheckCircle2 size={12} /> Cuenta Verificada
                            </div>
                        </div>
                    </div>

                    <div className="md:ml-auto">
                        <button className="px-6 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-2xl text-xs font-black uppercase tracking-widest shadow-sm hover:shadow-md transition-all flex items-center gap-2">
                            <Settings size={16} /> Editar Perfil
                        </button>
                    </div>
                </div>
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                
                {/* Left: General Progress & Courses (Col 7) */}
                <div className="lg:col-span-7 space-y-10">
                    <section className="glass dark:bg-slate-800/40 p-10 rounded-[3rem] border border-slate-200 dark:border-white/5 shadow-sm">
                        <div className="flex items-center justify-between mb-8">
                            <h3 className="text-xl font-black tracking-tighter">Progreso Académico</h3>
                            <span className="text-3xl font-black text-primary">74%</span>
                        </div>
                        <div className="w-full bg-slate-100 dark:bg-white/5 rounded-full h-4 overflow-hidden mb-4">
                            <div className="bg-primary h-full rounded-full shadow-[0_0_15px_rgba(25,115,240,0.6)] transition-all duration-1000" style={{ width: '74%' }}></div>
                        </div>
                        <p className="text-xs text-slate-500 font-medium leading-relaxed">
                            <span className="text-primary font-black">Próximo hito:</span> Certificación de Liderazgo Ministerial Nivel II. Te faltan 3 módulos para completar esta meta.
                        </p>
                    </section>

                    <section className="space-y-6">
                        <h3 className="text-2xl font-black tracking-tighter px-2">Carreras en Curso</h3>
                        <div className="grid gap-4">
                            {[
                                { title: 'Teología Sistemática I', info: 'Módulo 4 de 12', icon: BookOpen, color: 'text-primary' },
                                { title: 'Historia Eclesiástica', info: 'Módulo 2 de 8', icon: History, color: 'text-amber-500' }
                            ].map((c, i) => (
                                <div key={i} className="group glass dark:bg-slate-800/40 p-6 rounded-3xl border border-slate-200 dark:border-white/5 hover:border-primary/30 transition-all flex items-center gap-6 cursor-pointer">
                                    <div className={`size-14 rounded-2xl bg-white dark:bg-slate-900 flex items-center justify-center ${c.color} shadow-sm group-hover:scale-110 transition-transform border border-slate-100 dark:border-white/5`}>
                                        <c.icon size={24} />
                                    </div>
                                    <div className="flex-1">
                                        <h4 className="font-black text-slate-900 dark:text-white mb-1 group-hover:text-primary transition-colors">{c.title}</h4>
                                        <p className="text-xs text-slate-500 font-medium">En progreso • {c.info}</p>
                                    </div>
                                    <ChevronRight size={20} className="text-slate-300 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                                </div>
                            ))}
                        </div>
                    </section>
                </div>

                {/* Right: Badges & Stats (Col 5) */}
                <div className="lg:col-span-5 space-y-10">
                    <section className="bg-white dark:bg-slate-800/40 p-10 rounded-[3rem] border border-slate-200 dark:border-white/5 shadow-xl">
                        <div className="flex items-center justify-between mb-10">
                            <h3 className="text-xl font-black tracking-tighter">Mis Insignias</h3>
                            <button className="text-primary text-[10px] font-black uppercase tracking-widest hover:underline">Ver Todas</button>
                        </div>
                        <div className="grid grid-cols-2 gap-8">
                            {badges.map((b, i) => (
                                <div key={i} className={`flex flex-col items-center text-center gap-4 group ${!b.active && 'opacity-40 grayscale'}`}>
                                    <div className={`relative size-24 flex items-center justify-center rounded-full bg-gradient-to-br ${b.color} shadow-lg transition-transform group-hover:scale-110 duration-500`}>
                                        <div className="absolute inset-1.5 rounded-full border-2 border-white/20"></div>
                                        <b.icon size={40} className="text-white drop-shadow-md" />
                                    </div>
                                    <div>
                                        <p className="font-black text-slate-900 dark:text-white text-xs leading-tight mb-1">{b.name}</p>
                                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{b.desc}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="p-8 rounded-[3rem] bg-navy-dark text-white border border-white/5 shadow-2xl relative overflow-hidden group">
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,_var(--tw-gradient-stops))] from-primary/20 via-transparent to-transparent"></div>
                        <div className="relative z-10 flex items-center justify-between">
                            <div className="space-y-4">
                                <div className="flex items-center gap-3 text-primary">
                                    <TrendingUp size={20} />
                                    <span className="text-[10px] font-black uppercase tracking-widest">Rendimiento</span>
                                </div>
                                <h4 className="text-2xl font-black">Top 5%</h4>
                                <p className="text-slate-400 text-xs font-medium max-w-[180px]">Estás en el percentil más alto de tu cohorte este mes.</p>
                            </div>
                            <div className="size-24 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:rotate-12 transition-transform duration-500">
                                <span className="material-symbols-outlined text-5xl text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>military_tech</span>
                            </div>
                        </div>
                    </section>
                </div>

            </div>
        </div>
    );
}
