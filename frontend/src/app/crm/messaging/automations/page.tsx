'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Columns, UserPlus, PhoneCall, Home, HandHeart, CheckCircle2, ChevronRight, MoreVertical, Loader2, MessageSquare, Bell, Play, Pause, Trash2, Save, Link2, Users } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { toast } from 'react-toastify';
import { useAuth } from '@/context/AuthContext';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';

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
    const { token } = useAuth();

    const fetchAutomations = useCallback(async () => {
        if (!token) {
            setAutomations([]);
            setLoading(false);
            return;
        }
        try {
            const data = await apiFetch<Automation[]>('/crm/automations', { token, cache: 'no-store' });
            setAutomations(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchAutomations();
    }, [fetchAutomations]);

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
            const path = auto.id ? `/crm/automations/${auto.id}` : '/crm/automations';

            await apiFetch(path, {
                method: method as 'POST' | 'PUT',
                token,
                body: auto,
            });

            toast.success('Automatización guardada');
            fetchAutomations();
        } catch (err) {
            toast.error('Error al guardar');
        } finally {
            setSaving(false);
        }
    };

    const heroWatchers = ['Automations', 'Optimus Brain'];

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'CRM Pastoral', icon: Users }, { label: 'Automatizaciones', icon: Columns }]}
            rightActions={
                <button
                    onClick={handleAdd}
                    className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-200 transition-all"
                >
                    + Nueva regla
                </button>
            }
        >
        <AdminHero
            eyebrow="Automatizaciones"
            title="Automatizaciones de consolidación"
            description="Configura secuencias multicanal para cada etapa del pipeline; Optimus Brain sugiere delays y canales según engagement."
            tags={['Workflows', 'Plantillas', 'IA']}
            watchers={heroWatchers}
            primaryAction={{ label: 'Documentación', icon: Link2, onClick: () => {} }}
        />
        <div className="space-y-8 animate-in fade-in duration-500 max-w-5xl mx-auto pb-20">

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
        </CrmShell>
    );
}

