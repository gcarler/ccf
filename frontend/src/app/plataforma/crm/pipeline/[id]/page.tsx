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
                const data = await apiFetch<any>(`/crm/casos/${id}`, { token });
                if (!data) {
                    toast.error('Expediente no encontrado');
                    return;
                }
                setLead(data);
                setHistory([]);
            } catch (err) {
                toast.error('Error al cargar expediente del prospecto');
                setLead(null);
            } finally {
                setLoading(false);
            }
        };
        loadLead();
    }, [id, token]);

    if (loading) return <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Recuperando expediente ministerial...</div>;

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
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Información de Contacto</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="flex items-center gap-3 text-sm">
                                    <Phone size={16} className="text-[hsl(var(--text-secondary))]" />
                                    <span>{(lead.telefono ?? lead.phone) || 'Sin teléfono'}</span>
                                </div>
                                <div className="flex items-center gap-3 text-sm">
                                    <Mail size={16} className="text-[hsl(var(--text-secondary))]" />
                                    <span>{lead.email || 'Sin correo'}</span>
                                </div>
                            </div>
                        </DSCard>

                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-4">Notas de Seguimiento</h3>
                            <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed italic">
                                &quot;{lead.notes || 'Sin notas adicionales.'}&quot;
                            </p>
                        </DSCard>

                        <section className="space-y-4">
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Historial de Interacciones</h3>
                            <div className="space-y-3">
                                {history.map(item => (
                                    <div key={item.id} className="p-4 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                                        <div className="flex items-center gap-4">
                                            <div className="size-8 rounded-full bg-[hsl(var(--primary))/10] flex items-center justify-center text-[hsl(var(--primary))]">
                                                <Clock size={14} />
                                            </div>
                                            <div>
                                                <p className="text-xs font-bold">{item.action}</p>
                                                <p className="text-[10px] text-[hsl(var(--text-secondary))] uppercase font-bold">{item.actor}</p>
                                            </div>
                                        </div>
                                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">{item.date}</span>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>

                    <div className="space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Estado de Consolidación</h3>
                            <div className="space-y-3">
                                <div className="space-y-2">
                                    <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Etapa Actual</p>
                                    {(() => {
                                        const stageValue = lead.stage ?? 'new';
                                        return (
                                            <DSBadge
                                                tone={stageValue === 'consolidated' || stageValue === 'integrated' ? 'emerald' : 'blue'}
                                                label={STAGE_LABELS[stageValue] || stageValue.toUpperCase()}
                                            />
                                        );
                                    })()}
                                </div>
                                
                                <div className="h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                                
                                <button className="w-full py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-105 transition-all">
                                    Mover a Siguiente Etapa
                                </button>
                            </div>
                        </DSCard>

                        <div className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] rounded-md border border-[hsl(var(--border-primary))] text-[hsl(var(--text-primary))] space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--secondary))]">
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
