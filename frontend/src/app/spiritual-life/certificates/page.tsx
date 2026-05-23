"use client";

import React, { useEffect, useState } from 'react';
import {
    Award, Download, ShieldCheck, ExternalLink, Waves, FileCheck,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton from '@/components/ui/Skeleton';

interface Certificate {
    id: number;
    certificate_code: string;
    certificate_type: string | null;
    issued_at: string;
    enrollment_id: number;
    course_title?: string;
}

export default function DigitalCertificatesPage() {
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

    return (
        <div className="flex flex-col h-full bg-slate-50 dark:bg-[#0f1012] overflow-y-auto font-display">
            <div className="max-w-5xl mx-auto w-full p-3 space-y-6 pb-4">

                {/* Sub-header */}
                <div className="flex items-center justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <div className="size-7 rounded-lg bg-cyan-50 dark:bg-cyan-900/30 flex items-center justify-center">
                                <ShieldCheck size={14} className="text-cyan-600" />
                            </div>
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-cyan-600">Certificación Oficial</span>
                        </div>
                        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white leading-none">
                            Mis Certificados
                        </h1>
                        <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-0.5 font-medium">
                            Descarga tus actas y diplomas con validez digital dentro del ecosistema CCF.
                        </p>
                    </div>
                </div>

                {/* Certificates Grid */}
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-48 rounded-lg" />)}
                    </div>
                ) : certificates.length === 0 ? (
                    <EmptyState
                        icon={Award}
                        title="Aún no tienes certificados"
                        description="Cuando completes y apruebes un curso en la Academia CCF, tu certificado digital aparecerá aquí."
                        onAction={() => window.location.href = '/academy'}
                        actionLabel="Explorar Academia"
                    />
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {certificates.map((cert, i) => {
                            const isSacramento = cert.certificate_type?.toLowerCase().includes('bautismo') || cert.certificate_type?.toLowerCase().includes('sacramento');
                            return (
                                <motion.div
                                    key={cert.id}
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.07 }}
                                    className="group bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/[0.06] rounded-lg p-3 hover:border-cyan-300 dark:hover:border-cyan-500/30 hover:shadow-lg transition-all relative overflow-hidden"
                                >
                                    {/* Decorative watermark */}
                                    <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-[0.07] transition-all duration-700">
                                        <Award size={120} />
                                    </div>

                                    <div className="relative z-10 space-y-4">
                                        <div className="flex items-start justify-between">
                                            <div className="size-7 rounded-lg bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-100 dark:border-cyan-500/20 flex items-center justify-center text-cyan-600">
                                                {isSacramento ? <Waves size={24} /> : <FileCheck size={24} />}
                                            </div>
                                            <span className={clsx(
                                                "text-[9px] font-semibold uppercase tracking-wide px-2.5 py-1 rounded-full border",
                                                isSacramento
                                                    ? "bg-cyan-50 dark:bg-cyan-900/20 text-cyan-600 border-cyan-200 dark:border-cyan-500/20"
                                                    : "bg-blue-50 dark:bg-blue-900/20 text-blue-600 border-blue-200 dark:border-blue-500/20"
                                            )}>
                                                {cert.certificate_type ?? 'Academia'}
                                            </span>
                                        </div>

                                        <div>
                                            <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-tight">
                                                {cert.course_title ?? cert.certificate_type ?? 'Certificado'}
                                            </h3>
                                            <p className="font-semibold text-slate-400 uppercase tracking-wide mt-1">
                                                {new Date(cert.issued_at).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })}
                                            </p>
                                        </div>

                                        <div className="pt-3 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                                            <code className="text-[9px] font-mono text-slate-400 dark:text-slate-500">
                                                {cert.certificate_code}
                                            </code>
                                            <div className="flex items-center gap-2">
                                                <button className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-semibold uppercase tracking-wide rounded-lg active:scale-95 transition-all shadow-sm shadow-blue-500/20">
                                                    <Download size={12} /> PDF
                                                </button>
                                                <button className="p-1.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-500 dark:text-slate-400 rounded-lg transition-all">
                                                    <ExternalLink size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            );
                        })}
                    </div>
                )}

                {/* Verification Banner */}
                <div className="bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/[0.06] rounded-lg p-3 flex flex-col md:flex-row items-center gap-4 shadow-sm">
                    <div className="size-10 rounded-md bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-500/20 flex items-center justify-center text-emerald-600 shrink-0">
                        <ShieldCheck size={20} />
                    </div>
                    <div className="flex-1 text-center md:text-left">
                        <p className="text-[13px] font-bold text-slate-800 dark:text-white">Verificación de Autenticidad</p>
                        <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-0.5">
                            Cada certificado contiene un código único y token QR para validar su veracidad ante autoridades eclesiásticas.
                        </p>
                    </div>
                    <button className="shrink-0 px-4 py-1.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-700 dark:text-slate-300 text-[11px] font-semibold uppercase tracking-wide rounded-lg transition-all active:scale-95">
                        Validar Código
                    </button>
                </div>
            </div>
        </div>
    );
}

