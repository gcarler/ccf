"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import {
    ShieldAlert,
    Clock,
    User,
    Activity,
    LayoutDashboard,
    Globe,
    Lock
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

export default function AuditDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();

    const [log, setLog] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;

        const loadLog = async () => {
            try {
                setLoading(true);
                setLog({
                    id,
                    action: 'UPDATE_ROLE',
                    actor: 'Admin_Master',
                    target: 'user_id: 125',
                    timestamp: '2026-04-13T15:20:00Z',
                    description: 'Cambio de rol de "Estudiante" a "Docente" para el usuario juan.perez',
                    ip_address: '192.168.1.45',
                    metadata: {
                        old_role: 'student',
                        new_role: 'teacher',
                        reason: 'Promoción académica'
                    }
                });
            } catch {
                toast.error('Error al cargar el log de auditoría');
            } finally {
                setLoading(false);
            }
        };

        loadLog();
    }, [id, token]);

    if (loading) {
        return <div className="p-4 text-center animate-pulse font-semibold uppercase tracking-wide text-slate-400">Consultando bitácora de seguridad...</div>;
    }

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard, href: '/plataforma/admin' },
                    { label: 'Auditoría', icon: ShieldAlert, href: '/admin/audit' },
                    { label: `LOG-${id}`, icon: Activity },
                ]}
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
 <div className="w-full space-y-3">
                    <header className="space-y-4">
                        <div className="flex items-center gap-3">
                            <DSBadge tone="violet" label="SECURITY_LOG" />
                            <DSBadge tone="blue" label={log.action} />
                        </div>
                        <h1 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                            Detalle de Operación
                        </h1>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                        <div className="lg:col-span-2 space-y-3">
                            <DSCard>
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Descripción del Evento</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                                    {log.description}
                                </p>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Metadatos de la Transacción</h3>
                                <div className="bg-slate-900 rounded-lg p-3 overflow-x-auto">
                                    <pre className="text-emerald-400 text-xs font-mono">
                                        {JSON.stringify(log.metadata, null, 4)}
                                    </pre>
                                </div>
                            </DSCard>
                        </div>

                        <aside className="space-y-3">
                            <DSCard>
                                <div className="space-y-3">
                                    <div className="space-y-2">
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Actor</p>
                                        <div className="flex items-center gap-2">
                                            <div className="size-8 rounded-lg bg-slate-900 text-white flex items-center justify-center">
                                                <User size={16} />
                                            </div>
                                            <span className="text-xs font-semibold uppercase">{log.actor}</span>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Marca de Tiempo</p>
                                        <div className="flex items-center gap-2 text-xs font-bold text-slate-600 dark:text-slate-400">
                                            <Clock size={14} /> {new Date(log.timestamp).toLocaleString()}
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Dirección IP</p>
                                        <div className="flex items-center gap-2 text-xs font-bold text-slate-600 dark:text-slate-400">
                                            <Globe size={14} /> {log.ip_address}
                                        </div>
                                    </div>

                                    <div className="h-px bg-slate-100 dark:bg-white/5" />

                                    <div className="flex items-center gap-2 font-semibold text-emerald-600 uppercase tracking-wide">
                                        <Lock size={12} /> Registro Inmutable
                                    </div>
                                </div>
                            </DSCard>
                        </aside>
                    </div>
                </div>
            </main>
        </div>
    );
}
