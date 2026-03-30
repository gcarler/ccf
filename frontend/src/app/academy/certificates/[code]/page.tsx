"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import CertificateView from '@/components/academy/CertificateView';
import { Loader2, ShieldAlert } from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { GraduationCap } from 'lucide-react';

export default function PublicCertificatePage() {
    const params = useParams();
    const code = (params?.code as string) ?? null;
    const [certificate, setCertificate] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        const fetchCertificate = async () => {
            if (!code) {
                setError(true);
                setLoading(false);
                return;
            }
            try {
                // Public endpoint, no token needed for validation
                const data = await apiFetch(`/academy/certificates/validate/${code}`);
                setCertificate(data);
            } catch (err) {
                console.error("Error validating certificate:", err);
                setError(true);
            } finally {
                setLoading(false);
            }
        };
        fetchCertificate();
    }, [code]);

    if (loading) return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#1e1f21]">
            <Loader2 className="animate-spin text-blue-500" size={40} />
        </div>
    );

    if (error || !certificate) return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#1e1f21] p-6">
            <div className="max-w-md w-full text-center space-y-6 p-10 bg-white dark:bg-white/5 rounded-3xl border border-slate-200 dark:border-white/5 shadow-xl">
                <ShieldAlert size={64} className="text-rose-500 mx-auto" />
                <h2 className="text-2xl font-black text-slate-800 dark:text-white">Certificado No Válido</h2>
                <p className="text-slate-500 dark:text-slate-400">El código de certificado proporcionado no existe en nuestros registros oficiales.</p>
                <button 
                    onClick={() => window.location.href = '/'}
                    className="w-full py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-black text-xs uppercase tracking-widest"
                >
                    Volver al Inicio
                </button>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-[#1e1f21] overflow-y-auto py-12 px-6">
            <div className="max-w-5xl mx-auto space-y-12">
                <div className="flex flex-col items-center text-center space-y-4">
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded-full text-[10px] font-black uppercase tracking-widest border border-emerald-100 dark:border-emerald-900/40">
                        ✓ Certificado Verificado por CCF
                    </div>
                    <h1 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">Validación Oficial de Logro</h1>
                </div>
                
                <CertificateView data={certificate} />
                
                <p className="text-center text-[10px] text-slate-400 font-medium uppercase tracking-[0.2em]">
                    Este documento es una representación digital del certificado original emitido por el Centro Cristiano Familiar.
                </p>
            </div>
        </div>
    );
}
