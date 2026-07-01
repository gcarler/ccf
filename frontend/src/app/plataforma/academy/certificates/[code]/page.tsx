"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import CertificateView from '@/components/academy/CertificateView';
import { Loader2, ShieldAlert } from 'lucide-react';

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
        <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--surface-1))] dark:bg-[#1e1f21]">
            <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={40} />
        </div>
    );

    if (error || !certificate) return (
        <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--surface-1))] dark:bg-[#1e1f21] p-4">
            <div className="max-w-md w-full text-center space-y-3 p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-xl">
                <ShieldAlert size={64} className="text-rose-500 mx-auto" />
                <h2 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">Certificado No Valido</h2>
                <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">El codigo de certificado proporcionado no existe en nuestros registros oficiales.</p>
                <button
                    onClick={() => window.location.href = '/'}
                    className="w-full py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-black text-xs uppercase tracking-wide"
                >
                    Volver al Inicio
                </button>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-[hsl(var(--surface-1))] dark:bg-[#1e1f21] overflow-y-auto py-1.5 px-4">
 <div className="w-full space-y-3">
                <div className="flex flex-col items-center text-center space-y-4">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded-full text-[10px] font-semibold uppercase tracking-wide border border-emerald-100 dark:border-emerald-900/40">
                        Certificado Verificado por CCF
                    </div>
                    <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Validacion Oficial de Logro</h1>
                </div>

                <CertificateView data={certificate} />

                <p className="text-center text-[10px] text-[hsl(var(--text-secondary))] font-medium uppercase tracking-wide">
                    Este documento es una representacion digital del certificado original emitido por el Centro Cristiano Familiar.
                </p>
            </div>
        </div>
    );
}
