"use client";

import React, { useEffect, useState } from 'react';
import {
    Award, Download, ShieldCheck, ExternalLink, Waves, FileCheck,
    Loader2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface Certificate {
    id: number;
    certificate_code: string;
    certificate_type: string | null;
    issued_at: string;
    enrollment_id: number;
    course_title?: string;
}

export default function SpiritualCertificatesPanel() {
    const { token, user } = useAuth();
    const [certificates, setCertificates] = useState<Certificate[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !user?.id) { setLoading(false); return; }
        apiFetch<Certificate[]>(`/academy/me/certificates`, { token, cache: 'no-store' })
            .then(data => setCertificates(Array.isArray(data) ? data : []))
            .catch(() => setCertificates([]))
            .finally(() => setLoading(false));
    }, [token, user]);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-40 gap-3">
                <Loader2 className="animate-spin text-cyan-600" size={24} />
                <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Consultando registros...</p>
            </div>
        );
    }

    return (
        <div className="space-y-3 p-3">
            {certificates.length === 0 ? (
                <div className="text-center py-1.5 bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/10">
                    <Award className="mx-auto text-[hsl(var(--text-secondary))] dark:text-white/10 mb-4 animate-pulse" size={48} />
                    <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Sembrando esfuerzo para cosechar victoria</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {certificates.map((cert, i) => {
                        const isSacramento = cert.certificate_type?.toLowerCase().includes('bautismo') || cert.certificate_type?.toLowerCase().includes('sacramento');
                        return (
                            <motion.div
                                key={cert.id}
                                initial={{ opacity: 0, y: 15 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.1, type: 'spring', damping: 20 }}
                                className="group relative bg-[hsl(var(--bg-primary))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/[0.05] rounded-lg p-3 shadow-sm hover:shadow-2xl hover:shadow-blue-500/5 transition-all hover:border-blue-500/20"
                            >
                                <div className="absolute top-0 right-0 p-4 opacity-[0.05] group-hover:opacity-10 transition-opacity">
                                    <Award size={80} strokeWidth={1} />
                                </div>

                                <div className="flex items-start justify-between mb-3 relative z-10">
                                    <div className={clsx(
                                        "size-7 rounded-lg flex items-center justify-center border-2 shadow-lg transition-transform group-hover:scale-110",
                                        isSacramento ? "bg-cyan-500/10 border-cyan-500/20 text-cyan-500" : "bg-blue-500/10 border-blue-500/20 text-[hsl(var(--primary))]"
                                    )}>
                                        {isSacramento ? <Waves size={24} /> : <FileCheck size={24} />}
                                    </div>
                                    <span className={clsx(
                                        "text-[9px] font-semibold uppercase tracking-wider px-3 py-1.5 rounded-md border-2",
                                        isSacramento ? "bg-cyan-50 text-cyan-600 border-cyan-100 dark:bg-cyan-900/40 dark:border-cyan-500/30" : "bg-blue-50 text-[hsl(var(--primary))] border-blue-100 dark:bg-blue-900/40 dark:border-blue-500/30"
                                    )}>
                                        {cert.certificate_type || 'ACADEMIA'}
                                    </span>
                                </div>

                                <div className="space-y-2 mb-3 relative z-10">
                                    <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white leading-tight uppercase tracking-tight">
                                        {cert.course_title || cert.certificate_type}
                                    </h3>
                                    <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-2">
                                        <ShieldCheck size={12} className="text-emerald-500" /> Verificado {new Date(cert.issued_at).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
                                    </p>
                                </div>

                                <div className="pt-5 border-t border-[hsl(var(--border))] dark:border-white/[0.04] flex items-center justify-between relative z-10">
                                    <div className="space-y-0.5">
                                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide opacity-60">ID DE VALIDACIÓN</p>
                                        <code className="text-[10px] font-mono text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-bold tracking-tight">{cert.certificate_code}</code>
                                    </div>
                                    <div className="flex gap-2">
                                        <button className="px-3 py-2.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--primary))] text-white text-[10px] font-semibold uppercase tracking-wider rounded-lg shadow-lg active:scale-95 transition-all flex items-center gap-2">
                                            <Download size={14} /> PDF
                                        </button>
                                        <button className="p-2.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] rounded-lg transition-all active:scale-90">
                                            <ExternalLink size={16} />
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
