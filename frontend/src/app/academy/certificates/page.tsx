"use client";

import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Award, Download, Share2, School, Bell } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useStudentEnrollments } from '@/hooks/useStudentEnrollments';
import type { CertificateRecord } from '@/types/academy';
import CertificateModal from '@/components/CertificateModal';
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
    const [sharingId, setSharingId] = useState<number | null>(null);
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
            } catch (err: any) {
                if (!cancelled) {
                    setError(err?.detail?.message || 'No pudimos obtener tus certificados');
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
            setTimeout(() => setSharingId(null), 1000);
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
                watchers={['Academia Faro', 'Optimus Brain']}
                primaryAction={{ label: alertsEnabled ? 'Alertas activas' : 'Activar alertas', icon: Bell, onClick: () => {
                    setAlertsEnabled(true);
                    toast.success('Alertas de certificados activadas');
                } }}
            />
            <main className="rounded-md border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl overflow-hidden pb-4 relative z-10 hide-scrollbar">
                {totalLoading ? (
                    <div className="flex items-center justify-center py-1.5 text-slate-500 text-sm uppercase tracking-wide font-black">
                        Cargando historial...
                        </div>
                    ) : error ? (
                        <p className="px-4 py-1.5 text-center text-rose-400 font-semibold">{error}</p>
                    ) : certificates.length === 0 ? (
                        <div className="px-4 py-1.5 text-center text-slate-400 space-y-4">
                            <Award className="w-12 h-8 mx-auto text-slate-600" />
                            <p className="text-sm font-bold text-white">Aún no tienes certificados</p>
                            <p className="text-sm text-slate-400">Completa tus cursos para desbloquear diplomas y reconocimientos oficiales.</p>
                        </div>
                    ) : (
                        <>
                            <section className="mt-3 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <h2 className="px-4 text-slate-900 dark:text-white text-base font-bold mb-3 flex items-center gap-3">
                                    <Award className="text-yellow-500" size={24} /> Diplomas destacados
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
                                                <div className="aspect-[1.6/1] rounded-md relative overflow-hidden border border-white/10 shadow-2xl shadow-yellow-500/20 bg-gradient-to-br from-slate-800 to-slate-950 group-hover:border-primary/40 transition-all">
                                                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/15 via-transparent to-transparent opacity-80"></div>
                                                    <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center transform group-hover:scale-105 transition-transform duration-500">
                                                        <Award className="text-yellow-500 mb-3" size={48} />
                                                        <p className="text-[9px] uppercase tracking-wide text-yellow-500 font-bold">{certificate.certificate_type || 'Certificado'}</p>
                                                        <h3 className="text-base font-bold mt-2 text-white">
                                                            {enrollment?.course.title || 'Curso completado'}
                                                        </h3>
                                                        <p className="text-[10px] text-slate-400 italic mt-2">
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
                                <h3 className="text-slate-900 dark:text-white text-base font-bold mb-3">Todos mis títulos</h3>
                                <div className="flex flex-col gap-4">
                                    {certificates.map((certificate) => {
                                        const enrollment = resolveEnrollment(certificate);
                                        return (
                                            <div key={certificate.id} className="bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 hover:border-primary/30 rounded-md p-4 flex flex-col gap-4 shadow-xl transition-all">
                                                <div className="flex justify-between items-start gap-4">
                                                    <div className="flex gap-4 items-center">
                                                        <div className="size-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary shadow-inner border border-primary/20">
                                                            <School size={24} />
                                                        </div>
                                                        <div>
                                                            <h4 className="font-bold text-white text-sm leading-tight">{enrollment?.course.title || 'Curso completado'}</h4>
                                                            <p className="text-xs font-medium text-slate-400 mt-1">Código: {certificate.certificate_code}</p>
                                                            <p className="text-xs font-medium text-slate-500">Emitido el {new Date(certificate.issued_at).toLocaleDateString()}</p>
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={() => handleShare(certificate)}
                                                        className="p-2.5 rounded-md bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors border border-white/5"
                                                        disabled={sharingId === certificate.id}
                                                    >
                                                        <Share2 size={18} className={sharingId === certificate.id ? 'animate-pulse text-primary' : ''} />
                                                    </button>
                                                </div>
                                                <div className="flex gap-3">
                                                    <button
                                                        onClick={() => setActiveCertificate(certificate)}
                                                        className="flex-1 bg-white/5 hover:bg-primary/20 text-white py-2 rounded-md text-[10px] font-semibold uppercase tracking-wide flex items-center justify-center gap-3 transition-all border border-white/10 hover:border-primary/50"
                                                    >
                                                        <Download size={18} className="text-primary" />
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
                <CertificateModal
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

