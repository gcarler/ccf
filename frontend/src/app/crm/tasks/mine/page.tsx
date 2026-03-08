"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    Search,
    Calendar,
    History,
    MessageSquare,
    Phone,
    CheckCircle2,
    Home,
    Users,
    Settings,
    Plus,
    MapPin,
    MoreVertical
} from 'lucide-react';

interface Task {
    id: string;
    contactName: string;
    contactAvatar: string;
    type: string;
    status: 'Pendiente' | 'Atrasada' | 'Completada';
    priority: 'Alta' | 'Normal' | 'Baja';
    dueDate: string;
}

export default function MyTasks() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('pending');

    const tasks: Task[] = [
        {
            id: '1',
            contactName: 'Carlos Méndez',
            contactAvatar: 'https://i.pravatar.cc/150?u=20',
            type: 'Llamada de Bienvenida',
            status: 'Pendiente',
            priority: 'Alta',
            dueDate: 'Hoy'
        },
        {
            id: '2',
            contactName: 'Elena Rodríguez',
            contactAvatar: 'https://i.pravatar.cc/150?u=21',
            type: 'Visita Domiciliaria',
            status: 'Pendiente',
            priority: 'Normal',
            dueDate: 'Mañana'
        },
        {
            id: '3',
            contactName: 'Ricardo Santos',
            contactAvatar: 'https://i.pravatar.cc/150?u=22',
            type: 'Seguimiento Consolidación',
            status: 'Atrasada',
            priority: 'Alta',
            dueDate: 'Ayer'
        }
    ];

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Mesh Gradient Background */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-40 blur-3xl mix-blend-screen"></div>
                <div className="absolute top-1/2 left-0 w-[400px] h-[400px] bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-indigo-500/5 via-slate-950 to-slate-950 opacity-40 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 py-6 border-b border-white/5 flex items-center justify-between">
                    <button onClick={() => router.back()} className="text-slate-400 flex size-10 items-center justify-center rounded-full bg-white/5 hover:bg-primary/20 hover:text-primary transition-all cursor-pointer">
                        <ArrowLeft size={18} />
                    </button>
                    <h1 className="text-white text-lg font-black tracking-tight flex-1 text-center pr-10">Mis Tareas</h1>
                    <button className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary hover:bg-primary/20 transition-all">
                        <Search size={20} />
                    </button>
                </header>

                <main className="flex-1 overflow-y-auto hide-scrollbar pt-6 px-6 pb-32 animate-in fade-in slide-in-from-bottom-8 duration-700">
                    {/* Navigation Tabs */}
                    <section className="mb-8">
                        <div className="flex gap-10 justify-center">
                            {[
                                { id: 'pending', label: 'Pendientes' },
                                { id: 'completed', label: 'Completadas' },
                            ].map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`pb-4 text-xs font-black uppercase tracking-widest transition-all relative ${activeTab === tab.id ? 'text-primary' : 'text-slate-500 hover:text-slate-300'
                                        }`}
                                >
                                    {tab.label}
                                    {activeTab === tab.id && (
                                        <div className="absolute bottom-0 left-0 w-full h-1 bg-primary rounded-full shadow-[0_0_8px_#4242f0]"></div>
                                    )}
                                </button>
                            ))}
                        </div>
                    </section>

                    {/* Summary Cards */}
                    <section className="flex gap-4 mb-10 overflow-x-auto hide-scrollbar">
                        <div className="flex-1 min-w-[140px] bg-gradient-to-br from-primary to-primary-700 rounded-3xl p-6 text-white shadow-xl shadow-primary/20 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 -mr-10 -mt-10 size-32 bg-white/10 rounded-full blur-2xl group-hover:bg-white/20 transition-all"></div>
                            <div className="flex items-center gap-2 mb-4 relative z-10">
                                <Calendar size={14} className="text-blue-200" />
                                <span className="text-[10px] font-black uppercase tracking-widest text-blue-100">Hoy</span>
                            </div>
                            <h3 className="text-4xl font-black mb-1 relative z-10">8</h3>
                            <p className="text-[10px] font-bold text-blue-200 uppercase tracking-widest relative z-10">Tareas asignadas</p>
                        </div>
                        <div className="flex-1 min-w-[140px] bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 shadow-xl relative overflow-hidden group">
                            <div className="flex items-center gap-2 mb-4 text-rose-500">
                                <History size={14} />
                                <span className="text-[10px] font-black uppercase tracking-widest">Atrasadas</span>
                            </div>
                            <h3 className="text-4xl font-black text-white mb-1">3</h3>
                            <p className="text-[10px] font-black text-rose-500/60 uppercase tracking-widest">Acción inmediata</p>
                        </div>
                    </section>

                    {/* Tasks List */}
                    <section className="space-y-6">
                        <div className="flex items-center justify-between px-2">
                            <h3 className="text-white text-xl font-black tracking-tight uppercase tracking-widest">Próximas Acciones</h3>
                            <button className="text-[10px] font-black text-primary uppercase tracking-widest hover:underline transition-all">VER TODO</button>
                        </div>

                        <div className="space-y-4">
                            {tasks.map((task) => (
                                <div
                                    key={task.id}
                                    className={`bg-slate-900/40 backdrop-blur-xl border rounded-[2.5rem] p-6 shadow-xl transition-all relative overflow-hidden group ${task.status === 'Atrasada' ? 'border-rose-500/30' : 'border-white/5'
                                        }`}
                                >
                                    <div className="absolute top-6 right-6 flex items-center gap-2">
                                        <span className={`text-[9px] font-black px-3 py-1 rounded-full uppercase tracking-widest border ${task.priority === 'Alta' ? 'bg-rose-500/10 text-rose-500 border-rose-500/20' :
                                            'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                            }`}>
                                            {task.status === 'Atrasada' ? 'Atrasado' : task.priority}
                                        </span>
                                        <button className="text-slate-600 hover:text-white transition-colors">
                                            <MoreVertical size={16} />
                                        </button>
                                    </div>

                                    <div className="flex items-center gap-5 mb-8">
                                        <div className="size-16 rounded-2xl overflow-hidden border-2 border-white/10 group-hover:border-primary/50 transition-all shadow-lg shadow-black/40">
                                            <div className="size-full bg-slate-800 flex items-center justify-center text-white font-black uppercase">
                                                {task.contactName?.charAt(0)}
                                            </div>

                                        </div>
                                        <div>
                                            <h4 className="text-lg font-black text-white tracking-tight group-hover:text-primary transition-colors">{task.contactName}</h4>
                                            <p className="text-xs text-primary font-black uppercase tracking-widest mt-0.5">{task.type}</p>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between pt-6 border-t border-white/5">
                                        <div className="flex gap-2">
                                            <button className="size-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center hover:bg-emerald-500 hover:text-white transition-all border border-emerald-500/20 active:scale-90">
                                                <MessageSquare size={18} />
                                            </button>
                                            <button className={`size-10 rounded-xl flex items-center justify-center transition-all border active:scale-90 ${task.type === 'Visita Domiciliaria'
                                                ? 'bg-amber-500/10 text-amber-500 border-amber-500/20 hover:bg-amber-500 hover:text-white'
                                                : 'bg-primary/10 text-primary border-primary/20 hover:bg-primary hover:text-white'
                                                }`}>
                                                {task.type === 'Visita Domiciliaria' ? <MapPin size={18} /> : <Phone size={18} />}
                                            </button>
                                        </div>
                                        <button className="flex items-center gap-2 bg-white/5 hover:bg-primary text-slate-300 hover:text-white border border-white/10 hover:border-primary px-5 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all active:scale-95 shadow-lg hover:shadow-primary/20">
                                            <CheckCircle2 size={16} />
                                            Completar
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </main>

                {/* Navigation */}
                <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-2xl border-t border-white/5 px-8 pb-10 pt-4 flex justify-between items-center">
                    <button onClick={() => router.push('/crm/dashboard')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Home size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Inicio</span>
                    </button>
                    <button className="flex flex-col items-center gap-1.5 text-primary">
                        <CheckCircle2 size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Tareas</span>
                        <div className="size-1 rounded-full bg-primary mt-1 shadow-[0_0_8px_#4242f0]"></div>
                    </button>
                    <div className="relative -top-8 px-2">
                        <button className="bg-primary size-16 rounded-[2rem] text-white shadow-2xl shadow-primary/40 flex items-center justify-center border-4 border-slate-950 hover:scale-110 active:scale-90 transition-all">
                            <Plus size={32} />
                        </button>
                    </div>
                    <button onClick={() => router.push('/crm/contacts')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Users size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Personas</span>
                    </button>
                    <button className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Settings size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Perfil</span>
                    </button>
                </nav>
            </div>
        </div>
    );
}
