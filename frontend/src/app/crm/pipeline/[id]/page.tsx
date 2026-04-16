"use client";

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    User, Phone, Mail, Calendar, MapPin, 
    MessageSquare, History, PhoneCall, 
    CheckCircle2, Clock, AlertCircle, Save
} from 'lucide-react';
import CrmDetailShell from '@/components/crm/CrmDetailShell';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import DSBadge from '@/design/components/DSBadge';
import DSCard from '@/design/components/DSCard';

interface Lead {
    id: number;
    first_name: string;
    last_name: string;
    phone: string;
    source: string;
    stage: string;
    notes: string;
    created_at: string;
    assigned_pastor_id?: number;
}

interface CallLog {
    id: number;
    outcome: string;
    notes: string;
    created_at: string;
}

export default function LeadDetailPage() {
    const { id } = useParams();
    const { token } = useAuth();
    const router = useRouter();
    const [lead, setLead] = useState<Lead | null>(null);
    const [calls, setCalls] = useState<CallLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [newNote, setNewNote] = useState('');

    useEffect(() => {
        if (!token || !id) return;
        
        const fetchData = async () => {
            try {
                const leadData = await apiFetch<Lead>(`/crm/consolidation/pipeline/${id}`, { token });
                setLead(leadData);
                
                const callData = await apiFetch<CallLog[]>(`/crm/pipeline/leads/${id}/calls`, { token });
                setCalls(callData);
            } catch (error) {
                console.error("Error fetching lead data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [id, token]);

    const updateStage = async (newStage: string) => {
        if (!lead || !token) return;
        try {
            await apiFetch(`/crm/consolidation/pipeline/${id}`, {
                method: 'PATCH',
                token,
                body: JSON.stringify({ stage: newStage })
            });
            setLead({ ...lead, stage: newStage });
        } catch (error) {
            console.error("Error updating stage:", error);
        }
    };

    if (loading) return <div className="p-8 text-center">Cargando prospecto...</div>;
    if (!lead) return <div className="p-8 text-center text-rose-500">Prospecto no encontrado</div>;

    return (
        <CrmDetailShell
            title={`${lead.first_name} ${lead.last_name}`}
            description={`Prospecto desde ${new Date(lead.created_at).toLocaleDateString()}`}
            variant="indigo"
            rightAction={
                <DSBadge variant={lead.stage === 'converted' ? 'success' : 'warning'}>
                    {lead.stage.toUpperCase()}
                </DSBadge>
            }
        >
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Info Panel */}
                <div className="lg:col-span-1 space-y-6">
                    <DSCard title="Información de Contacto">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3 text-sm">
                                <Phone size={16} className="text-slate-400" />
                                <span>{lead.phone || 'Sin teléfono'}</span>
                            </div>
                            <div className="flex items-center gap-3 text-sm">
                                <Calendar size={16} className="text-slate-400" />
                                <span>Captado vía: {lead.source}</span>
                            </div>
                            <div className="flex items-center gap-3 text-sm">
                                <Clock size={16} className="text-slate-400" />
                                <span>Estado: {lead.stage}</span>
                            </div>
                        </div>
                        
                        <div className="mt-8 pt-6 border-t border-[hsl(var(--border))]">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4">Acciones de Pipeline</p>
                            <div className="grid grid-cols-2 gap-2">
                                <button 
                                    onClick={() => updateStage('contacted')}
                                    className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] text-[11px] font-semibold hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                                >
                                    MARCAR CONTACTADO
                                </button>
                                <button 
                                    onClick={() => updateStage('visiting')}
                                    className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] text-[11px] font-semibold hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                                >
                                    EN VISITA
                                </button>
                                <button 
                                    onClick={() => updateStage('converted')}
                                    className="px-3 py-2 rounded-lg bg-emerald-500 text-white text-[11px] font-semibold hover:bg-emerald-600 transition-colors col-span-2"
                                >
                                    CONVERTIR A MIEMBRO
                                </button>
                            </div>
                        </div>
                    </DSCard>
                </div>

                {/* Timeline & Notes */}
                <div className="lg:col-span-2 space-y-6">
                    <DSCard title="Seguimiento Pastoral">
                        <div className="space-y-6">
                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <textarea 
                                        value={newNote}
                                        onChange={(e) => setNewNote(e.target.value)}
                                        placeholder="Registrar nueva llamada o nota..."
                                        className="w-full h-24 bg-slate-50 dark:bg-white/5 border border-[hsl(var(--border))] rounded-xl p-4 text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                                    />
                                </div>
                                <button className="size-12 rounded-xl bg-indigo-500 text-white flex items-center justify-center self-end hover:bg-indigo-600 transition-colors shadow-lg shadow-indigo-500/20">
                                    <Save size={20} />
                                </button>
                            </div>

                            <div className="space-y-4">
                                <h4 className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Historial de Contacto</h4>
                                {calls.length === 0 ? (
                                    <div className="py-8 text-center text-slate-400 text-sm italic">
                                        No hay llamadas registradas aún.
                                    </div>
                                ) : (
                                    calls.map((call) => (
                                        <div key={call.id} className="flex gap-4 p-4 rounded-2xl bg-slate-50 dark:bg-white/5 border border-[hsl(var(--border))]">
                                            <div className="size-10 rounded-full bg-white dark:bg-white/10 flex items-center justify-center border border-[hsl(var(--border))] shrink-0">
                                                <PhoneCall size={16} className="text-indigo-500" />
                                            </div>
                                            <div className="flex-1 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-500">{call.outcome}</span>
                                                    <span className="text-[10px] text-slate-400">{new Date(call.created_at).toLocaleString()}</span>
                                                </div>
                                                <p className="text-sm text-[hsl(var(--text-secondary))]">{call.notes}</p>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </DSCard>
                </div>
            </div>
        </CrmDetailShell>
    );
}
