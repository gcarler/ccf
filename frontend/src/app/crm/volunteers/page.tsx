'use client';

import React, { useState, useEffect } from 'react';
import { Calendar, Users, Shield, CalendarCheck, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { apiUrl } from '@/lib/api';

interface Volunteer {
    id: number;
    name: string;
    role: string;
    status: string;
    assigned_event: string;
}

export default function VolunteersPage() {
    const [roles] = useState(['Ujieres', 'Seguridad', 'Alabanza', 'Multimedia', 'Infantil']);
    const [activeRole, setActiveRole] = useState('Ujieres');

    const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(apiUrl('/volunteers/'))
            .then(res => res.json())
            .then(data => {
                setVolunteers(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    return (
        <div className="space-y-8 animate-in fade-in duration-500 pb-20">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
                        <Shield className="text-indigo-600" /> Servidores y Voluntariado
                    </h1>
                    <p className="text-slate-500 mt-1">Organiza y asigna el equipo de servicio para los eventos locales.</p>
                </div>
                <button className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-black uppercase tracking-widest shadow-xl shadow-indigo-200 transition-all flex items-center gap-2">
                    <CalendarCheck size={16} /> Programar Rol
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* Sidebar Filter */}
                <div className="lg:col-span-1 space-y-4">
                    <div className="glass-card bg-white p-4 border border-slate-200">
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 px-2">Ministerios / Roles</h3>
                        <div className="space-y-2">
                            {roles.map(role => (
                                <button
                                    key={role}
                                    onClick={() => setActiveRole(role)}
                                    className={`w-full text-left px-4 py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-between ${activeRole === role
                                        ? 'bg-indigo-50 text-indigo-700'
                                        : 'hover:bg-slate-50 text-slate-600'
                                        }`}
                                >
                                    <span>{role}</span>
                                    {activeRole === role && <CheckCircle2 size={16} />}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="glass-card bg-gradient-to-br from-indigo-500 to-blue-600 text-white p-6 shadow-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16"></div>
                        <Users size={24} className="mb-4 text-indigo-200" />
                        <h4 className="text-2xl font-black mb-1">{volunteers.length} Servidores</h4>
                        <p className="text-xs uppercase tracking-widest text-indigo-200 font-bold">Activos este mes</p>
                    </div>
                </div>

                {/* Main Roster Panel */}
                <div className="lg:col-span-3">
                    <div className="glass-card bg-white p-6 md:p-8 border border-slate-200 min-h-[500px]">
                        <div className="flex justify-between items-center mb-8 pb-6 border-b border-slate-100">
                            <div>
                                <h2 className="text-2xl font-black text-slate-900">Programación: {activeRole}</h2>
                                <p className="text-sm font-bold text-slate-500">Eventos de la semana en curso</p>
                            </div>
                            <button className="px-4 py-2 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded-lg text-xs font-black uppercase tracking-widest transition-colors flex items-center gap-2">
                                <Calendar size={14} /> Ver Mes
                            </button>
                        </div>

                        <div className="space-y-4 relative min-h-[50px]">
                            {loading && (
                                <div className="absolute inset-0 bg-white/50 flex py-10 justify-center z-10 backdrop-blur-sm">
                                    <Loader2 className="animate-spin text-indigo-600" size={32} />
                                </div>
                            )}
                            {volunteers.filter(v => v.role === activeRole).map(vol => (
                                <div key={vol.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-2xl border border-slate-100 hover:border-indigo-100 bg-slate-50 hover:bg-white transition-all group">
                                    <div className="flex items-center gap-4 mb-4 sm:mb-0">
                                        <div className="w-10 h-10 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center font-black text-sm">
                                            {vol.name.charAt(0)}
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-slate-900 group-hover:text-indigo-600">{vol.name}</h4>
                                            <p className="text-xs font-bold text-slate-500">{vol.assigned_event}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4 justify-between sm:justify-end">
                                        <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1 ${vol.status === 'Confirmado'
                                            ? 'bg-emerald-100 text-emerald-700'
                                            : 'bg-amber-100 text-amber-700'
                                            }`}>
                                            {vol.status === 'Confirmado' ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                                            {vol.status}
                                        </span>
                                        <button className="text-slate-400 hover:text-red-500 text-xs font-bold px-2 transition-colors">
                                            Reasignar
                                        </button>
                                    </div>
                                </div>
                            ))}

                            {!loading && volunteers.filter(v => v.role === activeRole).length === 0 && (
                                <div className="py-20 text-center">
                                    <Shield size={48} className="mx-auto text-slate-200 mb-4" />
                                    <h4 className="text-lg font-black text-slate-900">No hay servidores asignados</h4>
                                    <p className="text-slate-500 text-sm">Añade voluntarios a este ministerio para el próximo evento.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
