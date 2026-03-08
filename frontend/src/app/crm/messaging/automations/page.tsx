'use client';

import React, { useState, useEffect } from 'react';
import { Columns, UserPlus, PhoneCall, Home, HandHeart, CheckCircle2, ChevronRight, MoreVertical, Loader2, MessageSquare, Bell, Play, Pause, Trash2, Save } from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { toast } from 'react-toastify';

interface Automation {
    id?: number;
    stage: string;
    delay_days: number;
    channel: string;
    template: string;
    is_active: boolean;
}

const STAGES = [
    { id: 'new', name: 'Contactos Nuevos' },
    { id: 'call', name: 'Llamada Inicial' },
    { id: 'visit', name: 'Visita / Casa de Gloria' },
    { id: 'discipleship', name: 'Discipulado Activo' },
    { id: 'consolidated', name: 'Bautizado / Consolidado' }
];

const CHANNELS = ['WhatsApp', 'SMS', 'Email'];

export default function CRMAutomationsPage() {
    const [automations, setAutomations] = useState<Automation[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchAutomations();
    }, []);

    const fetchAutomations = async () => {
        try {
            const res = await fetch(apiUrl('/crm/automations'));
            if (res.ok) {
                const data = await res.json();
                setAutomations(data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setAutomations([...automations, {
            stage: 'new',
            delay_days: 0,
            channel: 'WhatsApp',
            template: 'Hola {first_name}, ¡bienvenido a CCF! Estamos felices de tenerte con nosotros.',
            is_active: true
        }]);
    };

    const handleSave = async (index: number) => {
        setSaving(true);
        const auto = automations[index];
        try {
            const method = auto.id ? 'PUT' : 'POST';
            const url = auto.id ? apiUrl(`/crm/automations/${auto.id}`) : apiUrl('/crm/automations');

            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(auto)
            });

            if (res.ok) {
                toast.success('Automatización guardada');
                fetchAutomations();
            }
        } catch (err) {
            toast.error('Error al guardar');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500 max-w-5xl mx-auto pb-20">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
                        <Bell className="text-blue-600" /> Automatizaciones de Consolidación
                    </h1>
                    <p className="text-slate-500 mt-1">Configura mensajes automáticos que se envían cuando un contacto avanza en el proceso.</p>
                </div>
                <button
                    onClick={handleAdd}
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-black uppercase tracking-widest shadow-xl shadow-blue-200 transition-all"
                >
                    + Nueva Regla
                </button>
            </div>

            <div className="grid gap-6">
                {automations.map((auto, idx) => (
                    <div key={idx} className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm hover:shadow-md transition-all flex flex-col md:flex-row gap-6">
                        <div className="flex-1 space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="space-y-1">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Etapa del Pipeline</label>
                                    <select
                                        value={auto.stage}
                                        onChange={(e) => {
                                            const newAutos = [...automations];
                                            newAutos[idx].stage = e.target.value;
                                            setAutomations(newAutos);
                                        }}
                                        className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm font-bold text-slate-700 focus:outline-none focus:border-blue-500 transition-colors"
                                    >
                                        {STAGES.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                                    </select>
                                </div>
                                <div className="space-y-1">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Canal</label>
                                    <select
                                        value={auto.channel}
                                        onChange={(e) => {
                                            const newAutos = [...automations];
                                            newAutos[idx].channel = e.target.value;
                                            setAutomations(newAutos);
                                        }}
                                        className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm font-bold text-slate-700 focus:outline-none focus:border-blue-500 transition-colors"
                                    >
                                        {CHANNELS.map(c => <option key={c} value={c}>{c}</option>)}
                                    </select>
                                </div>
                                <div className="space-y-1">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Retraso (Días)</label>
                                    <input
                                        type="number"
                                        value={auto.delay_days}
                                        onChange={(e) => {
                                            const newAutos = [...automations];
                                            newAutos[idx].delay_days = parseInt(e.target.value);
                                            setAutomations(newAutos);
                                        }}
                                        className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm font-bold text-slate-700 focus:outline-none focus:border-blue-500 transition-colors"
                                    />
                                </div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Plantilla del Mensaje</label>
                                <textarea
                                    value={auto.template}
                                    onChange={(e) => {
                                        const newAutos = [...automations];
                                        newAutos[idx].template = e.target.value;
                                        setAutomations(newAutos);
                                    }}
                                    rows={3}
                                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-medium text-slate-700 focus:outline-none focus:border-blue-500 transition-colors resize-none"
                                    placeholder="Usa {first_name} para personalizar..."
                                />
                                <p className="text-[9px] text-slate-400 italic">Puedes usar etiquetas como {'{first_name}'}, {'{last_name}'}.</p>
                            </div>
                        </div>

                        <div className="flex flex-row md:flex-col justify-end gap-2 shrink-0 md:border-l md:border-slate-100 md:pl-6">
                            <button
                                onClick={() => handleSave(idx)}
                                disabled={saving}
                                className="flex-1 md:flex-none p-3 bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-600 hover:text-white transition-all flex items-center justify-center gap-2 font-bold text-xs"
                            >
                                <Save size={18} /> {auto.id ? 'Actualizar' : 'Guardar'}
                            </button>
                            <button
                                onClick={() => {
                                    const newAutos = [...automations];
                                    newAutos[idx].is_active = !newAutos[idx].is_active;
                                    setAutomations(newAutos);
                                    if (auto.id) handleSave(idx);
                                }}
                                className={`flex-1 md:flex-none p-3 rounded-xl transition-all flex items-center justify-center gap-2 font-bold text-xs ${auto.is_active ? 'bg-emerald-50 text-emerald-600 hover:bg-emerald-600 hover:text-white' : 'bg-slate-50 text-slate-400 hover:bg-slate-200'}`}
                            >
                                {auto.is_active ? <Pause size={18} /> : <Play size={18} />}
                                {auto.is_active ? 'Activo' : 'Pausado'}
                            </button>
                            <button className="flex-1 md:flex-none p-3 bg-red-50 text-red-600 rounded-xl hover:bg-red-600 hover:text-white transition-all flex items-center justify-center">
                                <Trash2 size={18} />
                            </button>
                        </div>
                    </div>
                ))}

                {automations.length === 0 && !loading && (
                    <div className="h-64 border-2 border-dashed border-slate-200 rounded-[40px] flex flex-col items-center justify-center text-slate-400 gap-4">
                        <Bell size={48} className="opacity-20" />
                        <p className="font-bold uppercase tracking-widest text-xs">No hay automatizaciones configuradas aún</p>
                        <button
                            onClick={handleAdd}
                            className="text-blue-600 font-black text-[10px] uppercase tracking-widest hover:underline"
                        >
                            Crear la primera regla
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
