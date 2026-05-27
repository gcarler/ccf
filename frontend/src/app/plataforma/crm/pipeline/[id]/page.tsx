"use client";

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { 
    Users, 
    MessageSquare, 
    Phone, 
    Mail, 
    Clock, 
    LayoutDashboard,
    User
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';
import CrmDetailShell from '@/components/crm/CrmDetailShell';

export default function LeadDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();
    
    const [lead, setLead] = useState<any>(null);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadLead = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/crm/consolidation/cases/${id}`, { token }).catch(() => null);
                setLead(data || {
                    id,
                    nombre_completo: 'Mateo González',
                    phone: '+57 300 123 4567',
                    email: 'mateo@example.com',
                    stage: 'call',
                    source: 'Invitación Directa',
                    notes: 'Joven universitario, interesado en el ministerio de música.'
                });
                
                setHistory([
                    { id: 1, action: 'Llamada realizada', date: '2026-04-10', actor: 'Pr. Juan' },
                    { id: 2, action: 'Visita programada', date: '2026-04-12', actor: 'Pr. Juan' }
                ]);
            } catch (err) {
                toast.error('Error al cargar expediente del prospecto');
            } finally {
                setLoading(false);
            }
        };
        loadLead();
    }, [id, token]);

    if (loading) return <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-slate-400">Recuperando expediente ministerial...</div>;

    const STAGE_LABELS: any = {
        'new': 'NUEVO',
        'call': 'POR LLAMAR',
        'visit': 'VISITA',
        'discipleship': 'DISCIPULADO',
        'consolidated': 'CONSOLIDADO',
        'contacted': 'POR LLAMAR',
        'visited': 'VISITA',
        'integrated': 'CONSOLIDADO',
        'lost': 'DESISTIÓ'
    };

    return (
        <div className="flex flex-col h-full">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'CRM', icon: LayoutDashboard, href: '/plataforma/crm' },
                    { label: 'Pipeline', icon: Users, href: '/plataforma/crm/pipeline' },
                    { label: lead.nombre_completo || '', icon: User },
                ]}
            />
            <CrmDetailShell
                title={lead.nombre_completo || ''}
                description={`Fuente: ${lead.source}`}
            >
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4 lg:p-4">
                    <div className="lg:col-span-2 space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-3">Información de Contacto</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="flex items-center gap-3 text-sm">
                                    <Phone size={16} className="text-slate-400" />
                                    <span>{(lead.telefono ?? lead.phone) || 'Sin teléfono'}</span>
                                </div>
                                <div className="flex items-center gap-3 text-sm">
                                    <Mail size={16} className="text-slate-400" />
                                    <span>{lead.email || 'Sin correo'}</span>
                                </div>
                            </div>
                        </DSCard>

                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-4">Notas de Seguimiento</h3>
                            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed italic">
                                &quot;{lead.notes || 'Sin notas adicionales.'}&quot;
                            </p>
                        </DSCard>

                        <section className="space-y-4">
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Historial de Interacciones</h3>
                            <div className="space-y-3">
                                {history.map(item => (
                                    <div key={item.id} className="p-4 rounded-lg bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-center justify-between">
                                        <div className="flex items-center gap-4">
                                            <div className="size-8 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-600">
                                                <Clock size={14} />
                                            </div>
                                            <div>
                                                <p className="text-xs font-bold">{item.action}</p>
                                                <p className="text-[10px] text-slate-400 uppercase font-bold">{item.actor}</p>
                                            </div>
                                        </div>
                                        <span className="text-[10px] font-bold text-slate-400">{item.date}</span>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>

                    <div className="space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-3">Estado de Consolidación</h3>
                            <div className="space-y-3">
                                <div className="space-y-2">
                                    <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">Etapa Actual</p>
                                    <DSBadge tone={lead.stage === 'consolidated' || lead.stage === 'integrated' ? 'emerald' : 'blue'} label={STAGE_LABELS[lead.stage] || lead.stage.toUpperCase()} />
                                </div>
                                
                                <div className="h-px bg-slate-100 dark:bg-white/5" />
                                
                                <button className="w-full py-1.5 bg-blue-600 text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-105 transition-all">
                                    Mover a Siguiente Etapa
                                </button>
                            </div>
                        </DSCard>

                        <div className="p-4 bg-slate-900 rounded-md text-white space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-emerald-400">
                                <MessageSquare size={14} /> Optimus Brain
                            </div>
                            <p className="text-[11px] font-medium leading-relaxed opacity-80">
                                Mateo muestra un alto interés en integrarse. Se recomienda invitarlo al próximo ensayo del ministerio de música este jueves.
                            </p>
                        </div>
                    </div>
                </div>
            </CrmDetailShell>
        </div>
    );
}
