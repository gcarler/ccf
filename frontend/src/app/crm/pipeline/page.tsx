'use client';

import React, { useState, useEffect } from 'react';
import { UserPlus, PhoneCall, Home, HandHeart, CheckCircle2, ChevronRight, MoreVertical, Loader2, Trash2, Bell, MessageSquare, List as ListIcon, LayoutGrid, Search, Filter, Plus, ChevronDown, Flag, User, Calendar as CalendarIcon, MessageCircle } from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { toast } from 'react-toastify';
import Link from 'next/link';

interface Lead {
    id: number;
    first_name: string;
    last_name: string;
    phone: string;
    source: string;
    stage: string;
    created_at: string;
}

export default function ConsolidationPipelinePage() {
    const [view, setView] = useState<'board' | 'list'>('board');
    const [stages] = useState([
        { id: 'new', name: 'Nuevos', color: 'bg-cu-blue', text: 'text-cu-blue', badge: 'bg-blue-50 text-cu-blue', icon: UserPlus },
        { id: 'call', name: 'Llamadas', color: 'bg-amber-500', text: 'text-amber-500', badge: 'bg-amber-50 text-amber-600', icon: PhoneCall },
        { id: 'visit', name: 'Visitas', color: 'bg-cu-purple', text: 'text-cu-purple', badge: 'bg-purple-50 text-cu-purple', icon: Home },
        { id: 'discipleship', name: 'Discipulado', color: 'bg-indigo-500', text: 'text-indigo-500', badge: 'bg-indigo-50 text-indigo-600', icon: HandHeart },
        { id: 'consolidated', name: 'Consolidados', color: 'bg-emerald-500', text: 'text-emerald-500', badge: 'bg-emerald-50 text-emerald-600', icon: CheckCircle2 }
    ]);

    const [leads, setLeads] = useState<Lead[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
    const [showCallModal, setShowCallModal] = useState(false);
    const [callNotes, setCallNotes] = useState('');
    const [prayerRequests, setPrayerRequests] = useState('');
    const [callOutcome, setCallOutcome] = useState('Exitoso');
    const [collapsedStages, setCollapsedStages] = useState<string[]>([]);

    useEffect(() => {
        fetchLeads();
    }, []);

    const fetchLeads = () => {
        setLoading(true);
        fetch(apiUrl('/pipeline/'))
            .then(res => res.json())
            .then(data => {
                if (Array.isArray(data)) {
                    setLeads(data);
                } else {
                    console.error('Expected array of leads, got:', data);
                    setLeads([]);
                }
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLeads([]);
                setLoading(false);
            });
    };

    const toggleStage = (id: string) => {
        setCollapsedStages(prev =>
            prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
        );
    };

    const handleAdvance = async (lead: Lead) => {
        const stageKeys = stages.map(s => s.id);
        const currentIndex = stageKeys.indexOf(lead.stage);

        if (currentIndex < stageKeys.length - 1) {
            const nextStage = stageKeys[currentIndex + 1];
            try {
                const res = await fetch(apiUrl(`/pipeline/${lead.id}`), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ stage: nextStage })
                });
                if (res.ok) {
                    toast.success(`Avanzado a ${stages[currentIndex + 1].name}`);
                    setLeads(leads.map(l => l.id === lead.id ? { ...l, stage: nextStage } : l));
                }
            } catch (err) {
                console.error(err);
            }
        }
    };

    const handleLogCall = async () => {
        if (!selectedLead) return;
        try {
            const res = await fetch(apiUrl('/crm/pipeline/calls'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lead_id: selectedLead.id,
                    pastor_id: 1,
                    outcome: callOutcome,
                    notes: callNotes,
                    prayer_requests: prayerRequests
                })
            });

            if (res.ok) {
                await fetch(apiUrl(`/pipeline/${selectedLead.id}`), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        notes: callNotes,
                        prayer_requests: prayerRequests
                    })
                });

                toast.success('Llamada registrada correctamente');
                setShowCallModal(false);
                setCallNotes('');
                setPrayerRequests('');
                fetchLeads();
            }
        } catch (err) {
            toast.error('Error al registrar llamada');
        }
    };

    const renderLeadCard = (lead: Lead) => (
        <div key={lead.id} className="bg-white dark:bg-slate-800/40 p-3 rounded-lg border border-slate-200 dark:border-white/5 shadow-sm hover:shadow-md hover:border-cu-purple/30 transition-all cursor-move group relative">
            <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                    <div className="size-6 rounded-md bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-500 uppercase shrink-0">
                        {lead.first_name.charAt(0)}{lead.last_name.charAt(0)}
                    </div>
                    <h4 className="font-bold text-slate-900 dark:text-white text-xs leading-tight truncate max-w-[140px]">
                        {lead.first_name} {lead.last_name}
                    </h4>
                </div>
                <button className="text-slate-300 hover:text-cu-purple transition-colors p-1">
                    <MoreVertical size={14} />
                </button>
            </div>

            <div className="flex items-center justify-between mt-3">
                <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 bg-slate-50 dark:bg-white/5 px-2 py-0.5 rounded">
                    {lead.source}
                </span>
                <span className="text-[9px] font-bold text-slate-400">
                    {new Date(lead.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                </span>
            </div>

            {/* Quick Actions Overlay */}
            <div className="absolute inset-0 bg-white/95 dark:bg-slate-900/95 flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-all rounded-lg scale-95 group-hover:scale-100 border border-cu-purple/20">
                <button
                    onClick={() => { setSelectedLead(lead); setShowCallModal(true); }}
                    className="p-2 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                    title="Llamar"
                >
                    <PhoneCall size={16} />
                </button>
                <button
                    onClick={() => handleAdvance(lead)}
                    className="p-2 text-cu-blue hover:bg-blue-50 rounded-lg transition-colors"
                    title="Avanzar"
                >
                    <ChevronRight size={18} />
                </button>
                <Link
                    href={`/crm/counseling?lead_id=${lead.id}`}
                    className="p-2 text-cu-purple hover:bg-purple-50 rounded-lg transition-colors"
                    title="Consejería"
                >
                    <MessageSquare size={16} />
                </Link>
            </div>
        </div>
    );

    const renderListRow = (lead: Lead) => {
        const stage = stages.find(s => s.id === lead.stage);

        return (
            <div key={lead.id} className="flex items-center px-4 py-1 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group border-b border-slate-100 dark:border-white/5 last:border-0 h-[36px]">
                <div className="w-[30%] flex items-center gap-2 overflow-hidden">
                    <div className="size-2 rounded-full border border-slate-300 dark:border-slate-600 group-hover:border-cu-purple transition-colors shrink-0"></div>
                    <div className="size-5 rounded bg-amber-100 text-amber-600 flex items-center justify-center text-[8px] font-bold shrink-0">
                        {lead.first_name.charAt(0)}
                    </div>
                    <span className="text-[12px] text-slate-700 dark:text-slate-300 truncate">
                        {lead.first_name} {lead.last_name}
                    </span>
                </div>

                <div className="w-[15%] flex items-center gap-2 px-2">
                    <User size={14} className="text-slate-300" />
                    <span className="text-[11px] text-slate-400">Sin asignar</span>
                </div>

                <div className="w-[15%] px-2">
                    <div className="flex items-center gap-2 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 transition-colors">
                        <CalendarIcon size={14} />
                        <span className="text-[11px]">Hoy</span>
                    </div>
                </div>

                <div className="w-[10%] px-2">
                    <Flag size={14} className="text-slate-300" />
                </div>

                <div className="w-[15%] px-2">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${stage?.badge || 'bg-slate-100 text-slate-500'}`}>
                        {stage?.name || lead.stage}
                    </span>
                </div>

                <div className="w-[15%] flex items-center justify-end gap-3 px-2">
                    <MessageCircle size={14} className="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer hover:text-cu-purple" />
                    <button className="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Plus size={14} />
                    </button>
                </div>
            </div>
        );
    };

    return (
        <div className="h-full flex flex-col space-y-4 animate-in fade-in duration-500 bg-white dark:bg-[#111418] overflow-hidden">
            {/* Control Bar (Sub-header ClickUp style) */}
            <div className="flex items-center justify-between px-6 pt-4 pb-2 border-b border-slate-200 dark:border-white/5">
                <div className="flex items-center gap-4">
                    <div className="flex bg-slate-100 dark:bg-white/5 p-1 rounded-lg">
                        <button
                            onClick={() => setView('board')}
                            className={`p-1.5 rounded-md transition-all ${view === 'board' ? 'bg-white dark:bg-slate-700 shadow-sm text-cu-purple' : 'text-slate-400'}`}
                        >
                            <LayoutGrid size={16} />
                        </button>
                        <button
                            onClick={() => setView('list')}
                            className={`p-1.5 rounded-md transition-all ${view === 'list' ? 'bg-white dark:bg-slate-700 shadow-sm text-cu-purple' : 'text-slate-400'}`}
                        >
                            <ListIcon size={16} />
                        </button>
                    </div>

                    <div className="h-6 w-[1px] bg-slate-200 dark:bg-white/10"></div>

                    <div className="flex items-center gap-1">
                        <button className="flex items-center gap-1.5 px-3 py-1.5 text-slate-500 hover:text-slate-800 dark:hover:text-white text-[11px] font-bold transition-all">
                            <Plus size={14} /> Añadir canal
                        </button>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-400">
                        <Search size={12} />
                        <input type="text" placeholder="Filtro" className="bg-transparent border-none outline-none text-[11px] w-24" />
                    </div>
                    <button className="text-slate-400 hover:text-slate-800 dark:hover:text-white"><Filter size={16} /></button>
                    <button className="text-slate-400 hover:text-slate-800 dark:hover:text-white"><Search size={16} /></button>
                    <button className="text-slate-400 hover:text-slate-800 dark:hover:text-white"><Plus size={16} /></button>
                </div>
            </div>

            {loading ? (
                <div className="flex-1 flex items-center justify-center">
                    <Loader2 className="animate-spin text-cu-purple" size={32} />
                </div>
            ) : view === 'board' ? (
                /* BOARD VIEW */
                <div className="flex-1 overflow-x-auto overflow-y-hidden flex gap-4 p-6 pt-2">
                    {stages.map(stage => {
                        const stageLeads = leads.filter(l => l.stage === stage.id);
                        return (
                            <div key={stage.id} className="min-w-[280px] w-[280px] flex flex-col bg-slate-50/50 dark:bg-white/5 rounded-xl shrink-0 group/stage">
                                <div className="p-4 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className={`size-3 rounded shadow-sm ${stage.color}`}></div>
                                        <h3 className="font-bold text-[11px] text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                                            {stage.name}
                                        </h3>
                                        <span className="text-[10px] font-bold text-slate-400 ml-1">
                                            {stageLeads.length}
                                        </span>
                                    </div>
                                    <Plus size={14} className="text-slate-400 opacity-0 group-hover/stage:opacity-100 cursor-pointer transition-opacity" />
                                </div>

                                <div className="px-2 pb-4 space-y-2 overflow-y-auto flex-1 scrollbar-thin scrollbar-thumb-slate-200">
                                    {stageLeads.map(lead => renderLeadCard(lead))}

                                    <button className="w-full py-3 border-2 border-dashed border-slate-200 dark:border-white/5 rounded-xl flex items-center justify-center text-[10px] font-black uppercase tracking-widest text-slate-400 hover:border-cu-purple/30 hover:text-cu-purple transition-all">
                                        + Añadir
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                /* LIST VIEW (Pixel Perfect ClickUp Refinement) */
                <div className="flex-1 overflow-y-auto px-6 pb-6">
                    {stages.map(stage => {
                        const stageLeads = leads.filter(l => l.stage === stage.id);
                        const isCollapsed = collapsedStages.includes(stage.id);

                        return (
                            <div key={stage.id} className="mb-6 last:mb-0">
                                {/* Group Header */}
                                <div className="flex items-center gap-2 mb-1 group/header">
                                    <button
                                        onClick={() => toggleStage(stage.id)}
                                        className="p-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded transition-all"
                                    >
                                        <ChevronDown size={14} className={`text-slate-400 transition-transform ${isCollapsed ? '-rotate-90' : ''}`} />
                                    </button>
                                    <div className={`flex items-center gap-2 px-2 py-0.5 rounded text-[11px] font-black uppercase tracking-widest shadow-sm ${stage.color} text-white`}>
                                        {stage.name}
                                    </div>
                                    <span className="text-[10px] font-bold text-slate-400">
                                        {stageLeads.length}
                                    </span>
                                    <Plus size={14} className="text-slate-300 opacity-0 group-hover/header:opacity-100 cursor-pointer ml-2 hover:text-cu-purple" />
                                </div>

                                {/* Table Header (Show only if not collapsed) */}
                                {!isCollapsed && (
                                    <div className="flex items-center px-4 py-2 border-b border-slate-100 dark:border-white/5 text-[10px] font-medium text-slate-400 bg-transparent">
                                        <div className="w-[30%]">Nombre</div>
                                        <div className="w-[15%] px-2">Persona asignada</div>
                                        <div className="w-[15%] px-2">Fecha límite</div>
                                        <div className="w-[10%] px-2">Prioridad</div>
                                        <div className="w-[15%] px-2">Estado</div>
                                        <div className="w-[15%] text-right px-2">Comentarios</div>
                                    </div>
                                )}

                                {/* Row Content */}
                                {!isCollapsed && (
                                    <div className="flex flex-col">
                                        {stageLeads.length > 0 ? (
                                            stageLeads.map(lead => renderListRow(lead))
                                        ) : (
                                            <div className="px-10 py-2 text-[11px] text-slate-400 italic">No hay registros</div>
                                        )}
                                        <button className="flex items-center gap-2 px-10 py-2 text-[11px] text-slate-400 hover:text-cu-purple transition-all group/add">
                                            <Plus size={12} className="group-hover:scale-110 transition-transform" />
                                            <span>Añadir Tarea</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {showCallModal && selectedLead && (
                <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-slate-900 w-full max-w-lg rounded-3xl shadow-2xl border border-slate-200 dark:border-white/5 p-8 space-y-6 animate-in zoom-in-95 duration-200">
                        <div className="flex justify-between items-start">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-amber-50 dark:bg-amber-500/10 rounded-2xl text-amber-600 dark:text-amber-500">
                                    <PhoneCall size={24} />
                                </div>
                                <div>
                                    <h2 className="text-xl font-bold dark:text-white leading-tight">Registrar Llamada Pastoral</h2>
                                    <p className="text-sm text-slate-500">Contactando a {selectedLead.first_name} {selectedLead.last_name}</p>
                                </div>
                            </div>
                            <button onClick={() => setShowCallModal(false)} className="text-slate-400 hover:text-slate-600 transition-colors">
                                <Trash2 size={20} />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Resultado</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {['Exitoso', 'Sin Respuesta', 'Ocupado', 'Volver a Llamar'].map(option => (
                                        <button
                                            key={option}
                                            onClick={() => setCallOutcome(option)}
                                            className={`py-2 rounded-xl text-xs font-bold border transition-all ${callOutcome === option ? 'bg-amber-50 border-amber-200 text-amber-600 dark:bg-amber-500/10 dark:border-amber-500/20' : 'bg-transparent border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5'}`}
                                        >
                                            {option}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            {/* ... more fields ... */}
                        </div>

                        <div className="flex gap-3 pt-4">
                            <button
                                onClick={() => setShowCallModal(false)}
                                className="flex-1 py-3 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-700 dark:text-slate-300 font-bold uppercase tracking-widest text-xs rounded-xl transition-all"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleLogCall}
                                className="flex-1 py-3 bg-slate-900 dark:bg-cu-purple hover:bg-slate-800 dark:hover:bg-cu-purple/90 text-white font-bold uppercase tracking-widest text-xs rounded-xl shadow-xl transition-all"
                            >
                                Guardar Registro
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
