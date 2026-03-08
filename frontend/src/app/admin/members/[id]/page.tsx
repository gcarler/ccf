"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    MoreVertical,
    Mail,
    Phone,
    Calendar,
    CheckCircle2,
    XCircle,
    BookOpen,
    FileText,
    UserMinus,
    UserCog,
    Verified,
    Plus
} from 'lucide-react';

export default function MemberDetailsAdmin({ params }: { params: { id: string } }) {
    const { isAuthenticated } = useAuth();
    const router = useRouter();

    const attendance = [
        { id: '1', event: 'Culto Dominical', date: '08 de Octubre, 2023', status: 'Asistió' },
        { id: '2', event: 'Casa de Gloria', date: '04 de Octubre, 2023', status: 'Ausente' },
        { id: '3', event: 'Culto Dominical', date: '01 de Octubre, 2023', status: 'Asistió' },
    ];

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Hero Area */}
            <div className="relative pt-10 pb-12 px-8 bg-gradient-to-b from-primary/10 to-transparent">
                <div className="flex items-center justify-between mb-10">
                    <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-[0.1em]">Perfil del Miembro</h1>
                    <button className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                        <MoreVertical size={20} />
                    </button>
                </div>

                <div className="flex flex-col items-center">
                    <div className="relative group">
                        <div className="size-36 rounded-[2.5rem] overflow-hidden border-4 border-white/10 group-hover:border-primary/50 transition-all shadow-2xl relative p-1 bg-primary/20">
                            <div className="size-full rounded-[2.2rem] bg-slate-800 flex items-center justify-center text-white text-3xl font-black">
                                {params.id.charAt(0).toUpperCase()}
                            </div>

                        </div>
                        <div className="absolute -bottom-2 -right-2 size-10 rounded-full bg-primary border-4 border-slate-950 flex items-center justify-center text-white shadow-xl">
                            <Verified size={20} className="fill-white/20" />
                        </div>
                    </div>
                    <div className="text-center mt-6 space-y-2">
                        <h2 className="text-3xl font-black tracking-tight text-white">Juan Pérez</h2>
                        <div className="inline-flex items-center px-4 py-1.5 text-[10px] font-black uppercase tracking-[0.2em] text-primary bg-primary/10 rounded-full border border-primary/20 shadow-lg shadow-primary/10">
                            Estudiante de Teología
                        </div>
                    </div>
                </div>
            </div>

            <main className="flex-1 px-8 pb-32 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Personal Info Grid */}
                <section>
                    <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 mb-4 ml-1">Información Personal</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {[
                            { icon: Mail, label: 'Email', value: 'juan.perez@iglesia.org' },
                            { icon: Phone, label: 'Teléfono', value: '+54 11 4567-8901' },
                            { icon: Calendar, label: 'Miembro desde', value: '12 de Octubre, 2022' },
                        ].map((item, idx) => (
                            <div key={idx} className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 flex items-center gap-5 group hover:border-primary/30 transition-all">
                                <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all shadow-lg">
                                    <item.icon size={20} />
                                </div>
                                <div>
                                    <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest">{item.label}</p>
                                    <p className="text-sm font-black text-white tracking-tight">{item.value}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Attendance History */}
                <section className="space-y-6">
                    <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 mb-4 ml-1">Historial de Asistencia</h3>

                    <div className="space-y-4">
                        <div className="flex gap-4 overflow-x-auto hide-scrollbar pb-2">
                            {[
                                { title: 'Culto Dominical', date: '15 Oct, 10:00 AM', active: true },
                                { title: 'Noche de Alabanza', date: '18 Oct, 07:30 PM', active: false },
                            ].map((event, i) => (
                                <div key={i} className={`flex-shrink-0 w-48 rounded-[2rem] p-6 border transition-all ${event.active ? 'bg-primary/20 border-primary/40' : 'bg-slate-900/40 border-white/5 opacity-60'}`}>
                                    <h4 className="text-sm font-black text-white truncate uppercase tracking-tight">{event.title}</h4>
                                    <p className="text-[10px] font-black text-slate-500 mt-2 flex items-center gap-2">
                                        <Calendar size={12} className="text-primary" /> {event.date}
                                    </p>
                                </div>
                            ))}
                        </div>

                        <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] overflow-hidden shadow-2xl">
                            {attendance.map((item) => (
                                <div key={item.id} className="flex items-center justify-between p-6 border-b border-white/5 group hover:bg-white/5 transition-all">
                                    <div className="flex items-center gap-5">
                                        <div className={`size-10 rounded-2xl flex items-center justify-center border transition-all ${item.status === 'Asistió' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-rose-500/10 text-rose-500 border-rose-500/20'}`}>
                                            {item.status === 'Asistió' ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-black text-white tracking-tight group-hover:text-primary transition-colors">{item.event}</h4>
                                            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">{item.date}</p>
                                        </div>
                                    </div>
                                    <span className={`text-[9px] px-3 py-1 rounded-lg font-black uppercase tracking-widest border ${item.status === 'Asistió' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-rose-500/10 text-rose-500 border-rose-500/20'}`}>
                                        {item.status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Academic Progress */}
                <section>
                    <div className="flex justify-between items-center mb-6 px-1">
                        <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600">Progreso Académico</h3>
                        <button className="text-[10px] font-black text-primary uppercase tracking-widest hover:underline">Ver todos</button>
                    </div>
                    <div className="bg-slate-920/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 space-y-8 shadow-2xl">
                        {[
                            { label: 'Fundamentos Teológicos', val: 85 },
                            { label: 'Liderazgo Ministerial', val: 42 },
                        ].map((course, i) => (
                            <div key={i} className="space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-xs font-black text-white uppercase tracking-tight">{course.label}</span>
                                    <span className="text-xs font-black text-primary">{course.val}%</span>
                                </div>
                                <div className="w-full bg-slate-950/50 h-2.5 rounded-full overflow-hidden border border-white/5 p-0.5">
                                    <div
                                        className="bg-gradient-to-r from-primary-400 to-primary h-full rounded-full transition-all duration-1000 shadow-[0_0_8px_#1973f0]"
                                        style={{ width: `${course.val}%` }}
                                    ></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Admin Notes */}
                <section>
                    <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 mb-4 ml-1">Muro de Notas</h3>
                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 space-y-6 shadow-2xl">
                        <div className="bg-slate-950/60 p-6 rounded-[2rem] border border-white/5 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 -mr-8 -mt-8 size-20 bg-primary/5 rounded-full blur-xl group-hover:bg-primary/10 transition-all"></div>
                            <p className="text-xs text-slate-400 leading-relaxed font-medium italic relative z-10">
                                &quot;Interesado en participar en el próximo retiro de líderes. Ha demostrado gran compromiso en las clases de los lunes.&quot;
                            </p>

                            <div className="mt-6 pt-4 border-t border-white/5 text-[9px] font-black text-slate-600 flex justify-between uppercase tracking-widest relative z-10">
                                <span>Por: Admin Pastor</span>
                                <span>Hace 2 días</span>
                            </div>
                        </div>
                        <button className="w-full py-4 border-2 border-dashed border-white/10 rounded-2xl flex items-center justify-center gap-2 text-slate-500 text-[10px] font-black uppercase tracking-[0.2em] hover:border-primary hover:text-primary transition-all active:scale-95">
                            <Plus size={14} />
                            Nueva nota administrativa
                        </button>
                    </div>
                </section>

                {/* Management Actions */}
                <section className="pb-12 text-center">
                    <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 mb-6">Acciones de Gestión</h3>
                    <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
                        <button className="flex items-center justify-center gap-3 bg-white/5 hover:bg-white/10 border border-white/5 py-5 rounded-2xl font-black text-[10px] text-white uppercase tracking-widest transition-all active:scale-95">
                            <UserCog size={18} className="text-primary" />
                            Cambiar Rol
                        </button>
                        <button className="flex items-center justify-center gap-3 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 py-5 rounded-2xl font-black text-[10px] text-rose-500 uppercase tracking-widest transition-all active:scale-95">
                            <UserMinus size={18} />
                            Desactivar
                        </button>
                    </div>
                </section>
            </main>
        </div>
    );
}
