"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { BookOpen, Upload, CreditCard, Wallet, Landmark, Lock, CheckCircle2, Loader2, ArrowRight } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

import { motion, AnimatePresence } from "framer-motion";
import { AcademyDetailContainer } from '@/components/academy/AcademyDetailShell';
import WorkspaceLayout from '@/components/WorkspaceLayout';

export default function EnrollmentWizard() {
    const { token, isAuthenticated, user } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const params = useParams<{ id: string }>();
    const courseId = params?.id ?? '';

    const [step, setStep] = useState(1);
    const [course, setCourse] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [enrolling, setEnrolling] = useState(false);
    const [paymentMethod, setPaymentMethod] = useState('card');

    useEffect(() => {
        if (!isAuthenticated) {
            router.push('/login');
            return;
        }

        const ctrl = new AbortController();

        const fetchCourse = async () => {
            try {
                const data = await apiFetch(`/academy/courses/${courseId}`, { cache: 'no-store', signal: ctrl.signal });
                setCourse(data);
            } catch (err: any) {
                if (err?.name === 'AbortError') return;
                addToast("Curso no encontrado", "error");
                router.push('/plataforma/academy');
            } finally {
                setLoading(false);
            }
        };

        fetchCourse();
        return () => ctrl.abort();
    }, [isAuthenticated, courseId, addToast, router]);

    const handleEnrollment = async () => {
        setEnrolling(true);
        try {
            await apiFetch("/academy/enrollments/", {
                method: "POST",
                token,
                body: { persona_id: user?.id, course_id: courseId }
            });
            addToast("¡Inscripción y pago exitosos!", "success");
            setStep(3); // Success step
        } catch {
            addToast("Error de conexión.", "error");
            setEnrolling(false);
        }
    };

    if (loading) {
        return (
            <WorkspaceLayout depth={2} breadcrumbs={[{ label: 'Academia' }, { label: 'Procesando curso…' }]} onBack={() => router.push('/plataforma/academy')}>
                <AcademyDetailContainer variant="blue" contentClassName="px-4 py-1.5">
                    <div className="flex items-center justify-center py-1.5">
                        <Loader2 className="animate-spin text-[hsl(var(--primary))] w-10 h-10" />
                    </div>
                </AcademyDetailContainer>
            </WorkspaceLayout>
        );
    }

    if (!course) return null;

    return (
        <WorkspaceLayout
            breadcrumbs={[{ label: 'Academia' }, { label: `Inscripción · ${course.title}` }]}
            onBack={() => router.push('/plataforma/academy')}
        >
            <AcademyDetailContainer variant="blue" contentClassName="max-w-xl mx-auto">
            <div className="px-4 mt-4 mb-4">
                <div className="flex items-center justify-between gap-4 p-2 bg-[hsl(var(--surface-2))] rounded-lg border border-[hsl(var(--border))]">
                    {[1, 2, 3].map((s) => (
                        <div key={s} className="flex-1 flex items-center gap-2">
                            <div className={`h-1 flex-1 rounded-full transition-all duration-500 ${step >= s ? 'bg-[hsl(var(--primary))] shadow-[0_0_8px_hsl(var(--primary)/0.5)]' : 'bg-[hsl(var(--border))]'}`}></div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="flex-1 px-4 pb-4">
                    <AnimatePresence mode="wait">
                        {step === 1 && (
                            <motion.div 
                                key="step1"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="space-y-3"
                            >
                                {/* Course Hero Card */}
                                <div className="relative group">
                                    <div className="absolute inset-0 bg-[hsl(var(--primary))] opacity-10 blur-2xl rounded-md group-hover:opacity-20 transition-opacity"></div>
                                    <div className="relative p-4 rounded-md bg-[hsl(var(--bg-muted))] border border-white/10 overflow-hidden min-h-[220px] flex flex-col justify-end">
                                        <div className="absolute top-0 right-0 p-4 text-white/5 opacity-20 transform translate-x-4 -translate-y-4 group-hover:scale-110 group-hover:rotate-6 transition-all duration-700">
                                            <BookOpen size={160} strokeWidth={1} />
                                        </div>
                                        <div className="relative z-10">
                                            <span className="inline-block px-3 py-1 rounded-full bg-white/10 border border-white/10 text-[9px] font-semibold uppercase tracking-wide text-white mb-4">
                                                {course.modality === 'formal' ? 'Ruta Formal' : 'Ruta No Formal'}
                                            </span>
                                            <h1 className="text-xl font-bold text-white leading-none tracking-tighter mb-2">{course.title}</h1>
                                            <p className="text-white/60 text-xs font-bold uppercase tracking-wide">{course.code}</p>
                                        </div>
                                    </div>
                                </div>

                                {/* Quick Specs */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="p-3 rounded-md bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1">Carga Horaria</p>
                                        <p className="text-sm font-semibold">{course.duration_hours}h <span className="text-[10px] text-[hsl(var(--text-secondary))]">Estimadas</span></p>
                                    </div>
                                    <div className="p-3 rounded-md bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1">Modalidad</p>
                                        <p className="text-sm font-semibold">{course.is_self_paced ? 'Sincrónico' : 'Híbrido'}</p>
                                    </div>
                                </div>

                                {/* Enrollment Info */}
                                <div className="surface-card p-4 border-none bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="size-8 rounded-md bg-[hsl(var(--primary)/0.1)] border border-[hsl(var(--primary)/0.2)] flex items-center justify-center text-[hsl(var(--primary))]">
                                            <BookOpen size={20} />
                                        </div>
                                        <h3 className="font-black text-sm uppercase tracking-wide">Contenido Curricular</h3>
                                    </div>
                                    <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed text-justify mb-4">
                                        {course.description || "Este curso ha sido diseñado para proporcionar una base sólida en principios ministeriales y liderazgo efectivo."}
                                    </p>
                                    {course.modality === 'formal' && (
                                        <div className="pt-4 border-t border-[hsl(var(--border))]">
                                            <p className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide mb-4">Documentación Necesaria</p>
                                            <div className="space-y-3">
                                                <button className="w-full group flex items-center justify-between p-4 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.5)] transition-all">
                                                    <div className="flex items-center gap-3">
                                                        <CreditCard size={18} className="text-[hsl(var(--text-secondary))]" />
                                                        <span className="text-[11px] font-bold">Identificación Oficial</span>
                                                    </div>
                                                    <Upload size={16} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]" />
                                                </button>
                                                <button className="w-full group flex items-center justify-between p-4 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.5)] transition-all">
                                                    <div className="flex items-center gap-3">
                                                        <BookOpen size={18} className="text-[hsl(var(--text-secondary))]" />
                                                        <span className="text-[11px] font-bold">Registro de Calificaciones</span>
                                                    </div>
                                                    <Upload size={16} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]" />
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        )}

                        {step === 2 && (
                            <motion.div 
                                key="step2"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="space-y-3"
                            >
                                <div className="surface-card p-4 bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]">
                                    <div className="flex flex-col items-center text-center mb-3">
                                        <div className="size-8 rounded-lg bg-[hsl(var(--primary)/0.1)] border border-[hsl(var(--primary)/0.2)] flex items-center justify-center text-[hsl(var(--primary))] mb-4">
                                            <Wallet size={32} />
                                        </div>
                                        <h3 className="text-base font-bold tracking-tighter mb-1">Resumen de Cargo</h3>
                                        <p className="text-xs text-[hsl(var(--text-secondary))] font-medium">Inscripción al ciclo académico actual</p>
                                    </div>

                                    <div className="space-y-4 pt-4">
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Matrícula Base</span>
                                            <span className="font-semibold">$200.00 USD</span>
                                        </div>
                                        <div className="flex justify-between items-center text-xs pb-4 border-b border-[hsl(var(--border))]">
                                            <span className="font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Derechos de Admisión</span>
                                            <span className="font-semibold">$50.00 USD</span>
                                        </div>
                                        <div className="flex justify-between items-center bg-[hsl(var(--surface-3))] p-4 rounded-lg">
                                            <span className="text-[11px] font-semibold uppercase tracking-wide">Inversión Total</span>
                                            <span className="text-lg font-bold text-[hsl(var(--primary))] tracking-tighter">$250.00</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide ml-1 mb-2">Método de Financiamiento</p>
                                    <div className="grid grid-cols-1 gap-3">
                                        {['card', 'paypal', 'bank'].map((id) => (
                                            <label key={id} className={`flex items-center gap-4 p-3 rounded-lg border transition-all cursor-pointer ${paymentMethod === id ? 'bg-[hsl(var(--primary)/0.1)] border-[hsl(var(--primary)/0.5)]' : 'bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]'}`}>
                                                <input type="radio" name="pay-opt" value={id} className="hidden" onChange={(e) => setPaymentMethod(e.target.value)} checked={paymentMethod === id} />
                                                <div className={`size-9 rounded-md flex items-center justify-center border transition-all ${paymentMethod === id ? 'bg-[hsl(var(--primary))] border-[hsl(var(--primary))] text-white shadow-lg shadow-primary/20' : 'bg-[hsl(var(--surface-2))] border-[hsl(var(--border))] text-[hsl(var(--text-secondary))]'}`}>
                                                    {id === 'card' && <CreditCard size={24} />}
                                                    {id === 'paypal' && <Wallet size={24} />}
                                                    {id === 'bank' && <Landmark size={24} />}
                                                </div>
                                                <div className="flex-1">
                                                    <p className="text-xs font-semibold uppercase tracking-wider">{id === 'card' ? 'Tarjeta de Crédito' : id === 'paypal' ? 'PayPal Checkout' : 'Depósito Directo'}</p>
                                                    <p className="text-[10px] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide">{id === 'card' ? 'Mastercard / Visa' : 'Transferencia Segura'}</p>
                                                </div>
                                                {paymentMethod === id && <CheckCircle2 size={20} className="text-[hsl(var(--primary))]" />}
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {step === 3 && (
                            <motion.div 
                                key="step3"
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="flex flex-col items-center justify-center pt-12 text-center"
                            >
                                <div className="relative mb-3">
                                    <div className="absolute inset-0 bg-[hsl(var(--success))]/20 blur-3xl animate-pulse"></div>
                                    <div className="relative size-10 rounded-md bg-[hsl(var(--success))] border border-[hsl(var(--success)/40%)] flex items-center justify-center text-white shadow-2xl shadow-[hsl(var(--success)/30%)]">
                                        <CheckCircle2 size={64} strokeWidth={2.5} />
                                    </div>
                                </div>
                                <h2 className="text-lg font-bold tracking-tighter mb-4 leading-none">¡Bienvenido!</h2>
                                <p className="text-sm text-[hsl(var(--text-secondary))] font-medium leading-relaxed max-w-[280px] mb-3">
                                    Tu inscripción a <span className="font-semibold">{course.title}</span> ha sido procesada con éxito.
                                </p>
                                <button
                                    onClick={() => router.push('/plataforma/academy')}
                                    className="w-full py-2 rounded-lg bg-[hsl(var(--text-primary))] text-[hsl(var(--bg-primary))] font-semibold uppercase tracking-wide text-xs hover:opacity-90 active:scale-95 transition-all shadow-xl"
                                >
                                    Ir a mi Academia
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

            {step < 3 && (
                <div className="sticky bottom-0 left-0 w-full p-4 bg-gradient-to-t from-[hsl(var(--bg-primary))] via-[hsl(var(--bg-primary)/0.9)] to-transparent">
                         <button
                            onClick={() => {
                                if (step === 1) setStep(2);
                                else if (step === 2) handleEnrollment();
                            }}
                            disabled={enrolling}
                            className="w-full h-8 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-semibold uppercase tracking-wide text-[11px] shadow-2xl shadow-primary/30 flex items-center justify-center gap-3 active:scale-[0.98] transition-all hover:brightness-110 disabled:opacity-50"
                        >
                            {enrolling ? (
                                <><Loader2 className="animate-spin w-5 h-5" /> Encriptando...</>
                            ) : (
                                <>
                                    {step === 1 ? 'Iniciar Inscripción' : 'Confirmar Participación'}
                                    <ArrowRight size={18} />
                                </>
                            )}
                        </button>
                        {step === 2 && (
                             <div className="flex items-center justify-center gap-2 mt-3">
                                <Lock size={12} className="text-[hsl(var(--success))]" />
                                <p className="text-[9px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Transacción Encriptada 256-bit SSL</p>
                             </div>
                        )}
                    </div>
                )}
            </AcademyDetailContainer>
        </WorkspaceLayout>
    );
}
