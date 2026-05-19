"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import { ShieldAlert, Terminal, Lock, User, Activity, RefreshCw, Eye } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface AuditLog {
    id: number;
    actor_user_id: number;
    action: string;
    resource_type: string;
    resource_id: string;
    created_at: string;
    metadata: any;
}

export default function SecurityAuditPage() {
    const router = useRouter();
    const { token, isAuthenticated } = useAuth();
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchLogs = async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<AuditLog[]>('/admin/audit', { token, cache: 'no-store' });
            setLogs(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isAuthenticated) fetchLogs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isAuthenticated, token]);

    if (!isAuthenticated) return null;

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Seguridad', icon: ShieldAlert },
                { label: 'Caja Negra (Audit Log)', icon: Terminal }
            ]}
        >
            <style jsx global>{`
                .cyber-grid {
                    background-image: 
                        linear-gradient(rgba(16, 185, 129, 0.05) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(16, 185, 129, 0.05) 1px, transparent 1px);
                    background-size: 20px 20px;
                }
                .scanline {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 10px;
                    background: linear-gradient(to bottom, transparent, rgba(16, 185, 129, 0.4), transparent);
                    animation: scan 4s linear infinite;
                    pointer-events: none;
                    z-index: 50;
                }
                @keyframes scan {
                    0% { top: -10px; }
                    100% { top: 100%; }
                }
            `}</style>

            <div className="flex flex-col h-full bg-[#0a0f16] rounded-[3rem] overflow-hidden border border-emerald-900/30 shadow-2xl relative font-mono">
                {/* Cyberpunk Header */}
                <div className="p-8 border-b border-emerald-900/50 bg-black/40 flex justify-between items-center relative z-10 shrink-0">
                    <div className="flex items-center gap-6">
                        <div className="size-16 rounded-2xl bg-emerald-950/50 flex items-center justify-center text-emerald-500 border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
                            <Lock size={32} />
                        </div>
                        <div>
                            <h1 className="text-2xl font-black text-emerald-400 uppercase tracking-[0.3em] flex items-center gap-3">
                                Control de Acceso Maestro
                                <span className="flex size-3 relative">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-500 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full size-3 bg-rose-500"></span>
                                </span>
                            </h1>
                            <p className="text-[10px] text-emerald-600 uppercase tracking-widest mt-1">Registro inmutable de transacciones del sistema</p>
                        </div>
                    </div>
                    <button 
                        onClick={fetchLogs}
                        className="px-6 py-2.5 bg-emerald-950/50 text-emerald-400 border border-emerald-500/30 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-900 transition-colors flex items-center gap-2 group"
                    >
                        <RefreshCw size={14} className="group-hover:rotate-180 transition-transform duration-700" />
                        Sincronizar
                    </button>
                </div>

                {/* Main Console Area */}
                <div className="flex-1 overflow-hidden relative cyber-grid">
                    <div className="scanline" />
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#0a0f16]/50 to-[#0a0f16] pointer-events-none z-10" />
                    
                    <div className="h-full overflow-y-auto p-8 relative z-20 scrollbar-thin scrollbar-thumb-emerald-900/50 scrollbar-track-transparent">
                        {loading ? (
                            <div className="flex flex-col items-center justify-center py-40 gap-4">
                                <Activity className="text-emerald-500 animate-pulse" size={48} />
                                <p className="text-emerald-500/70 text-[10px] uppercase tracking-[0.5em] animate-pulse">Descifrando registros...</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <AnimatePresence>
                                    {logs.map((log, idx) => (
                                        <motion.div 
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            key={log.id}
                                            onClick={() => router.push(`/admin/audit/${log.id}`)}
                                            className="group flex flex-col md:flex-row md:items-center gap-4 p-4 rounded-xl bg-black/40 border border-emerald-900/20 hover:border-emerald-500/50 hover:bg-emerald-950/20 transition-all cursor-crosshair"
                                        >
                                            <div className="flex items-center gap-4 w-full md:w-auto md:min-w-[200px] shrink-0">
                                                <span className="text-emerald-700 text-[10px]">[{new Date(log.created_at).toLocaleTimeString('en-US', { hour12: false })}]</span>
                                                <span className={clsx(
                                                    "px-2 py-0.5 rounded text-[9px] uppercase tracking-widest font-black",
                                                    log.action.includes('delete') || log.action.includes('remove') ? "bg-rose-950/50 text-rose-500 border border-rose-900" :
                                                    log.action.includes('update') || log.action.includes('edit') ? "bg-amber-950/50 text-amber-500 border border-amber-900" :
                                                    "bg-emerald-950/50 text-emerald-400 border border-emerald-900"
                                                )}>
                                                    {log.action}
                                                </span>
                                            </div>

                                            <div className="flex-1 flex items-center gap-4 text-emerald-400/80 text-xs">
                                                <User size={12} className="opacity-50" /> 
                                                <span>USR_ID: {log.actor_user_id || 'SYS'}</span>
                                                <span className="opacity-30">|</span>
                                                <span>Target: <span className="text-emerald-300 font-bold">{log.resource_type?.toUpperCase()}</span> #{log.resource_id}</span>
                                            </div>

                                            <div className="shrink-0 flex items-center gap-3">
                                                <div className="text-[9px] text-emerald-600/50 uppercase tracking-widest hidden lg:block truncate max-w-[200px]">
                                                    {JSON.stringify(log.metadata)}
                                                </div>
                                                <button 
                                                    onClick={(e) => { e.stopPropagation(); router.push(`/admin/audit/${log.id}`); }}
                                                    className="p-2 bg-emerald-950/50 rounded-lg text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-emerald-900"
                                                >
                                                    <Eye size={14} />
                                                </button>
                                            </div>
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                            </div>
                        )}
                    </div>
                </div>

                {/* Status Bar */}
                <div className="p-2 border-t border-emerald-900/50 bg-black text-emerald-700 text-[9px] uppercase tracking-[0.2em] flex justify-between shrink-0 relative z-10">
                    <span>SYS_STATUS: ONLINE</span>
                    <span>CONNECTION: SECURE_SOCKET</span>
                    <span>DB_SYNC: OK</span>
                </div>
            </div>
        </AdminShell>
    );
}

