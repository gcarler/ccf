"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import CertificateView from '@/components/academy/CertificateView';
import { Loader2, ShieldAlert } from 'lucide-react';

// H-11 (cierre 2026-07-24): tipo local mirror del schema público
// ``schemas.CertificateValidation`` — sustituye el useState no tipado.
interface ValidatedCertificate {
    certificate_code: string;
    issued_at: string;
    certificate_type: string;
    enrollment: {
        student: { username: string };
        course: { title: string };
    };
}

export default function PublicCertificatePage() {
    const params = useParams();
    const router = useRouter();
    const code = (params?.code as string) ?? null;
    const [certificate, setCertificate] = useState<ValidatedCertificate | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        const ctrl = new AbortController();
        const fetchCertificate = async () => {
            if (!code) {
                setError(true);
                setLoading(false);
                return;
            }
            try {
                const data = await apiFetch<ValidatedCertificate>(`/academy/certificates/validate/${code}`, { signal: ctrl.signal });
                setCertificate(data);
            } catch (err: unknown) {
                if (!(err instanceof DOMException && err.name === 'AbortError')) {
                }
                setError(true);
            } finally {
                setLoading(false);
            }
        };
        fetchCertificate();
        return () => ctrl.abort();
    }, [code]);

    if (loading) return (
        <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--surface-1))]">
            <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={40} />
        </div>
    );

    if (error || !certificate) return (
        <div className="min-h-screen flex items-center justify-center bg-[hsl(var(--surface-1))] p-4">
            <div className="max-w-md w-full text-center space-y-3 p-3 bg-[hsl(var(--surface-2))] rounded-lg border border-[hsl(var(--border))] shadow-xl">
                <ShieldAlert size={64} className="text-[hsl(var(--destructive))] mx-auto" />
                <h2 className="text-lg font-bold text-[hsl(var(--foreground))]">Certificado No Valido</h2>
                <p className="text-[hsl(var(--muted-foreground))]">El codigo de certificado proporcionado no existe en nuestros registros oficiales.</p>
                <button
                    onClick={() => router.push('/')}
                    className="w-full py-1.5 bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] border border-[hsl(var(--border))] rounded-lg font-black text-xs uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] transition-colors"
                >
                    Volver al Inicio
                </button>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-[hsl(var(--surface-1))] overflow-y-auto py-1.5 px-4">
            <div className="w-full space-y-3">
                <div className="flex flex-col items-center text-center space-y-4">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))] rounded-full text-2xs font-semibold uppercase tracking-wide border border-[hsl(var(--success)/0.3)]">
                        Certificado Verificado por CCF
                    </div>
                    <h1 className="text-lg font-bold text-[hsl(var(--foreground))] tracking-tight">Validacion Oficial de Logro</h1>
                </div>

                <CertificateView data={certificate} />

                <p className="text-center text-2xs text-[hsl(var(--muted-foreground))] font-medium uppercase tracking-wide">
                    Este documento es una representacion digital del certificado original emitido por el Centro Cristiano Familiar.
                </p>
            </div>
        </div>
    );
}
