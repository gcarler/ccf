"use client";

import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { Award, Download, Share2, School, Bell } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useStudentEnrollments } from '@/hooks/useStudentEnrollments';
import type { CertificateRecord } from '@/types/academy';
import CertificateDrawer from '@/components/CertificateDrawer';
import AdminHero from '@/components/admin/AdminHero';
import { toast } from 'sonner';

export default function StudentCertificates() {
    const { user, token, isAuthenticated } = useAuth();
    const userId = user?.id;
    const { enrollments, loading: loadingEnrollments } = useStudentEnrollments();
    const [certificates, setCertificates] = useState<CertificateRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeCertificate, setActiveCertificate] = useState<CertificateRecord | null>(null);
    const [sharingId, setSharingId] = useState<string | null>(null);
    const [alertsEnabled, setAlertsEnabled] = useState(false);

    useEffect(() => {
        if (!userId || !token || !isAuthenticated) return;
        let cancelled = false;
        async function fetchCertificates() {
            setLoading(true);
            setError(null);
            try {
                const data = await apiFetch<CertificateRecord[]>(`/academy/me/certificates`, {
                    token,
                    cache: 'no-store',
                });
                if (!cancelled) {
                    setCertificates(Array.isArray(data) ? data : []);
                }
            } catch (err: unknown) {
                // H-11 (cierre 2026-07-24): catch unknown — extrae mensaje
                // del shape HTTP ``{detail: {message: string}}`` o de Error.
                if (!cancelled) {
                    const message =
                        (err && typeof err === 'object' && 'detail' in err &&
                            typeof (err as { detail?: { message?: string } }).detail?.message === 'string'
                            ? (err as { detail: { message: string } }).detail.message
                            : undefined) ||
                        (err instanceof Error ? err.message : undefined) ||
                        'No pudimos obtener tus certificados';
                    setError(message);
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        }
        fetchCertificates();
        return () => {
            cancelled = true;
        };
    }, [userId, token, isAuthenticated]);

    const featured = useMemo(() => certificates.slice(0, 3), [certificates]);

    const resolveEnrollment = (certificate: CertificateRecord) =>
        enrollments.find((en) => en.id === certificate.enrollment_id);

    const totalLoading = loading || loadingEnrollments;

    const shareTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const handleShare = useCallback((certificate: CertificateRecord) => {
        try {
            setSharingId(certificate.id);
            const base = typeof window !== 'undefined' ? window.location.origin : '';
            const url = `${base}/academy/certificates/${certificate.certificate_code}`;
            if (navigator?.clipboard) {
                navigator.clipboard.writeText(url).then(() => toast.success('Enlace copiado'));
            } else {
                toast.message('Comparte este enlace', { description: url });
            }
        } finally {
            if (shareTimerRef.current) clearTimeout(shareTimerRef.current);
            shareTimerRef.current = setTimeout(() => setSharingId(null), 1000);
        }
    }, []);

    if (!isAuthenticated) return null;

    return (
        <div className="space-y-3 px-4 py-1.5">
            <AdminHero
                eyebrow="Certificados"
                title="Mis certificados"
                description="Diplomas por nivel de formación: Básico, Intermedio y Misión Global."
                tags={['Básico', 'Intermedio', 'Misión Global']}
                watchers={['Academia CCF', 'Optimus Brain']}
                primaryAction={{ label: alertsEnabled ? 'Alertas activas' : 'Activar alertas', icon: Bell, onClick: () => {
                    setAlertsEnabled(true);
                    toast.success('Alertas de certificados activadas');
                } }}
            />
            <main className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-xl overflow-hidden pb-4 relative z-10 hide-scrollbar">
                {totalLoading ? (
                    <div className="flex items-center justify-center py-1.5 text-[hsl(var(--text-secondary))] text-sm uppercase tracking-wide font-black">
                        Cargando historial...
                        </div>
                    ) : error ? (
                        <p className="px-4 py-1.5 text-center text-[hsl(var(--danger))] font-semibold">{error}</p>
                    ) : certificates.length === 0 ? (
                        <div className="px-4 py-1.5 text-center text-[hsl(var(--text-secondary))] space-y-4">
                            <Award className="w-12 h-8 mx-auto text-[hsl(var(--text-secondary))]" />
                            <p className="text-sm font-bold text-[hsl(var(--foreground))]">Aún no tienes certificados</p>
                            <p className="text-sm text-[hsl(var(--text-secondary))]">Completa tus cursos para desbloquear diplomas y reconocimientos oficiales.</p>
                        </div>
                    ) : (
                        <>
                            <section className="mt-3 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <h2 className="px-4 text-[hsl(var(--foreground))] text-base font-bold mb-3 flex items-center gap-3">
                                    <Award className="text-[hsl(var(--warning))]" size={24} /> Diplomas destacados
                                </h2>
                                <div className="flex overflow-x-auto hide-scrollbar gap-3 px-4 snap-x pb-6">
                                    {featured.map((certificate) => {
                                        const enrollment = resolveEnrollment(certificate);
                                        return (
                                            <button
                                                key={certificate.id}
                                                onClick={() => setActiveCertificate(certificate)}
                                                className="min-w-[260px] snap-center group text-left"
                                            >
                                                <div className="aspect-[1.6/1] rounded-md relative overflow-hidden border border-[hsl(var(--border))] shadow-2xl bg-[hsl(var(--surface-2))] group-hover:border-[hsl(var(--primary)/0.4)] transition-all">
                                                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[hsl(var(--primary)/0.15)] via-transparent to-transparent opacity-80"></div>
                                                    <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center transform group-hover:scale-105 transition-transform duration-500">
                                                        <Award className="text-[hsl(var(--warning))] mb-3" size={48} />
                                                        <p className="text-2xs uppercase tracking-wide text-[hsl(var(--warning))] font-bold">{certificate.certificate_type || 'Certificado'}</p>
                                                        <h3 className="text-base font-bold mt-2 text-[hsl(var(--foreground))]">
                                                            {enrollment?.course.title || 'Curso completado'}
                                                        </h3>
                                                        <p className="text-2xs text-[hsl(var(--text-secondary))] italic mt-2">
                                                            Emitido el {new Date(certificate.issued_at).toLocaleDateString()}
                                                        </p>
                                                    </div>
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            </section>

                            <section className="mt-3 px-4 animate-in fade-in slide-in-from-bottom-6 duration-700">
                                <h3 className="text-[hsl(var(--foreground))] text-base font-bold mb-3">Todos mis títulos</h3>
                                <div className="flex flex-col gap-4">
                                    {certificates.map((certificate) => {
                                        const enrollment = resolveEnrollment(certificate);
                                        return (
                                            <div key={certificate.id} className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] rounded-md p-4 flex flex-col gap-4 shadow-xl transition-all">
                                                <div className="flex justify-between items-start gap-4">
                                                    <div className="flex gap-4 items-center">
                                                        <div className="size-7 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] shadow-inner border border-[hsl(var(--primary)/0.2)]">
                                                            <School size={24} />
                                                        </div>
                                                        <div>
                                                            <h4 className="font-bold text-[hsl(var(--foreground))] text-sm leading-tight">{enrollment?.course.title || 'Curso completado'}</h4>
                                                            <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-1">Código: {certificate.certificate_code}</p>
                                                            <p className="text-xs font-medium text-[hsl(var(--text-secondary))]">Emitido el {new Date(certificate.issued_at).toLocaleDateString()}</p>
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={() => handleShare(certificate)}
                                                        className="p-2.5 rounded-md bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3))] transition-colors border border-[hsl(var(--border))]"
                                                        disabled={sharingId === certificate.id}
                                                    >
                                                        <Share2 size={18} className={sharingId === certificate.id ? 'animate-pulse text-[hsl(var(--primary))]' : ''} />
                                                    </button>
                                                </div>
                                                <div className="flex gap-3">
                                                    <button
                                                        onClick={() => setActiveCertificate(certificate)}
                                                        className="flex-1 bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--primary)/0.2)] text-[hsl(var(--foreground))] py-2 rounded-md text-2xs font-semibold uppercase tracking-wide flex items-center justify-center gap-3 transition-all border border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.5)]"
                                                    >
                                                        <Download size={18} className="text-[hsl(var(--primary))]" />
                                                        Ver / Descargar
                                                    </button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </section>
                        </>
                    )}
            </main>

            {activeCertificate && (
                <CertificateDrawer
                    certificate={activeCertificate}
                    enrollment={
                        resolveEnrollment(activeCertificate) || {
                            id: activeCertificate.enrollment_id,
                            course: { title: 'Curso', modality: 'formal' },
                        }
                    }
                    userName={user?.username || 'Estudiante'}
                    onClose={() => setActiveCertificate(null)}
                />
            )}
        </div>
    );
}
