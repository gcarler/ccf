"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { BookOpen, Upload, CreditCard, Wallet, Landmark, Lock, CheckCircle2, Loader2, ArrowRight } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

import { motion, AnimatePresence } from "framer-motion";
import AcademyDetailShell from '@/components/academy/AcademyDetailShell';

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

        const fetchCourse = async () => {
            try {
                const data = await apiFetch(`/academy/courses/${courseId}`, { cache: 'no-store' });
                setCourse(data);
            } catch {
                addToast("Curso no encontrado", "error");
                router.push('/academy');
            } finally {
                setLoading(false);
            }
        };

        fetchCourse();
        // router is stable in Next.js app router
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isAuthenticated, courseId, addToast]);

    const handleEnrollment = async () => {
        setEnrolling(true);
        try {
            await apiFetch("/academy/enrollments/", {
                method: "POST",
                token,
                body: { user_id: user?.id, course_id: parseInt(courseId) }
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
            <AcademyDetailShell title="Procesando curso" description="Preparando requisitos de inscripción" variant="violet">
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="animate-spin text-[hsl(var(--primary))] w-10 h-10" />
                </div>
            </AcademyDetailShell>
        );
    }

    if (!course) return null;

    return (
        <AcademyDetailShell
            title={`Inscripción · ${course.title}`}
            description="Completa requisitos, realiza pago y confirma tu nivel de formación"
            variant="violet"
            contentClassName="max-w-xl mx-auto"
        >
            <div className="px-4 mt-4 mb-4">
                <div className="flex items-center justify-between gap-4 p-2 bg-[hsl(var(--surface-2))] rounded-2xl border border-[hsl(var(--border))]">
                    {[1, 2, 3].map((s) => (
                        <div key={s} className="flex-1 flex items-center gap-2">
                            <div className={`h-1 flex-1 rounded-full transition-all duration-500 ${step >= s ? 'bg-[hsl(var(--primary))] shadow-[0_0_8px_hsl(var(--primary)/0.5)]' : 'bg-[hsl(var(--border))]'}`}></div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="flex-1 px-4 pb-32">
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
                                    <div className="absolute inset-0 bg-[hsl(var(--primary))] opacity-10 blur-2xl rounded-xl group-hover:opacity-20 transition-opacity"></div>
                                    <div className="relative p-4 rounded-xl bg-slate-900 border border-white/10 overflow-hidden min-h-[220px] flex flex-col justify-end">
                                        <div className="absolute top-0 right-0 p-4 text-white/5 opacity-20 transform translate-x-4 -translate-y-4 group-hover:scale-110 group-hover:rotate-6 transition-all duration-700">
                                            <BookOpen size={160} strokeWidth={1} />
                                        </div>
                                        <div className="relative z-10">
                                            <span className="inline-block px-3 py-1 rounded-full bg-white/10 border border-white/10 text-[9px] font-black uppercase tracking-[0.2em] text-white mb-4">
                                                {course.modality === 'formal' ? 'Ruta Formal' : 'Ruta No Formal'}
                                            </span>
                                            <h1 className="text-3xl font-black text-white leading-none tracking-tighter mb-2">{course.title}</h1>
                                            <p className="text-white/60 text-xs font-bold uppercase tracking-widest">{course.code}</p>
                                        </div>
                                    </div>
                                </div>

                                {/* Quick Specs */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="p-5 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                                        <p className="text-[10px] font-black text-[hsl(var(--text-secondary))] uppercase tracking-widest mb-1">Carga Horaria</p>
                                        <p className="text-sm font-black">{course.duration_hours}h <span className="text-[10px] text-[hsl(var(--text-secondary))]">Estimadas</span></p>
                                    </div>
                                    <div className="p-5 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                                        <p className="text-[10px] font-black text-[hsl(var(--text-secondary))] uppercase tracking-widest mb-1">Modalidad</p>
                                        <p className="text-sm font-black">{course.is_self_paced ? 'Sincrónico' : 'Híbrido'}</p>
                                    </div>
                                </div>

                                {/* Enrollment Info */}
                                <div className="surface-card p-4 border-none bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="size-8 rounded-xl bg-[hsl(var(--primary)/0.1)] border border-[hsl(var(--primary)/0.2)] flex items-center justify-center text-[hsl(var(--primary))]">
                                            <BookOpen size={20} />
                                        </div>
                                        <h3 className="font-black text-sm uppercase tracking-widest">Contenido Curricular</h3>
                                    </div>
                                    <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed text-justify mb-4">
                                        {course.description || "Este curso ha sido diseñado para proporcionar una base sólida en principios ministeriales y liderazgo efectivo."}
                                    </p>
                                    {course.modality === 'formal' && (
                                        <div className="pt-4 border-t border-[hsl(var(--border))]">
                                            <p className="text-[10px] font-black text-[hsl(var(--primary))] uppercase tracking-widest mb-4">Documentación Necesaria</p>
                                            <div className="space-y-3">
                                                <button className="w-full group flex items-center justify-between p-4 rounded-2xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.5)] transition-all">
                                                    <div className="flex items-center gap-3">
                                                        <CreditCard size={18} className="text-[hsl(var(--text-secondary))]" />
                                                        <span className="text-[11px] font-bold">Identificación Oficial</span>
                                                    </div>
                                                    <Upload size={16} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]" />
                                                </button>
                                                <button className="w-full group flex items-center justify-between p-4 rounded-2xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.5)] transition-all">
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
                                    <div className="flex flex-col items-center text-center mb-8">
                                        <div className="size-16 rounded-[1.5rem] bg-[hsl(var(--primary)/0.1)] border border-[hsl(var(--primary)/0.2)] flex items-center justify-center text-[hsl(var(--primary))] mb-4">
                                            <Wallet size={32} />
                                        </div>
                                        <h3 className="text-base font-black tracking-tighter mb-1">Resumen de Cargo</h3>
                                        <p className="text-xs text-[hsl(var(--text-secondary))] font-medium">Inscripción al ciclo académico actual</p>
                                    </div>

                                    <div className="space-y-4 pt-4">
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="font-bold text-[hsl(var(--text-secondary))] uppercase tracking-widest">Matrícula Base</span>
                                            <span className="font-black">$200.00 USD</span>
                                        </div>
                                        <div className="flex justify-between items-center text-xs pb-4 border-b border-[hsl(var(--border))]">
                                            <span className="font-bold text-[hsl(var(--text-secondary))] uppercase tracking-widest">Derechos de Admisión</span>
                                            <span className="font-black">$50.00 USD</span>
                                        </div>
                                        <div className="flex justify-between items-center bg-[hsl(var(--surface-3))] p-4 rounded-2xl">
                                            <span className="text-[11px] font-black uppercase tracking-widest">Inversión Total</span>
                                            <span className="text-lg font-black text-[hsl(var(--primary))] tracking-tighter">$250.00</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <p className="text-[10px] font-black text-[hsl(var(--text-secondary))] uppercase tracking-[0.25em] ml-1 mb-2">Método de Financiamiento</p>
                                    <div className="grid grid-cols-1 gap-3">
                                        {['card', 'paypal', 'bank'].map((id) => (
                                            <label key={id} className={`flex items-center gap-4 p-5 rounded-2xl border transition-all cursor-pointer ${paymentMethod === id ? 'bg-[hsl(var(--primary)/0.1)] border-[hsl(var(--primary)/0.5)]' : 'bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]'}`}>
                                                <input type="radio" name="pay-opt" value={id} className="hidden" onChange={(e) => setPaymentMethod(e.target.value)} checked={paymentMethod === id} />
                                                <div className={`size-9 rounded-xl flex items-center justify-center border transition-all ${paymentMethod === id ? 'bg-[hsl(var(--primary))] border-[hsl(var(--primary))] text-white shadow-lg shadow-primary/20' : 'bg-[hsl(var(--surface-2))] border-[hsl(var(--border))] text-[hsl(var(--text-secondary))]'}`}>
                                                    {id === 'card' && <CreditCard size={24} />}
                                                    {id === 'paypal' && <Wallet size={24} />}
                                                    {id === 'bank' && <Landmark size={24} />}
                                                </div>
                                                <div className="flex-1">
                                                    <p className="text-xs font-black uppercase tracking-wider">{id === 'card' ? 'Tarjeta de Crédito' : id === 'paypal' ? 'PayPal Checkout' : 'Depósito Directo'}</p>
                                                    <p className="text-[10px] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-widest">{id === 'card' ? 'Mastercard / Visa' : 'Transferencia Segura'}</p>
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
                                <div className="relative mb-8">
                                    <div className="absolute inset-0 bg-emerald-500/20 blur-3xl animate-pulse"></div>
                                    <div className="relative size-32 rounded-xl bg-emerald-500 border border-emerald-400 flex items-center justify-center text-white shadow-2xl shadow-emerald-500/30">
                                        <CheckCircle2 size={64} strokeWidth={2.5} />
                                    </div>
                                </div>
                                <h2 className="text-4xl font-black tracking-tighter mb-4 leading-none">¡Bienvenido!</h2>
                                <p className="text-sm text-[hsl(var(--text-secondary))] font-medium leading-relaxed max-w-[280px] mb-10">
                                    Tu inscripción a <span className="text-[hsl(var(--text-primary))] font-black">{course.title}</span> ha sido procesada con éxito.
                                </p>
                                <button
                                    onClick={() => router.push('/academy')}
                                    className="w-full py-5 rounded-2xl bg-[hsl(var(--text-primary))] text-[hsl(var(--bg-primary))] font-black uppercase tracking-widest text-xs hover:opacity-90 active:scale-95 transition-all shadow-xl"
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
                            className="w-full h-16 rounded-2xl bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-black uppercase tracking-[0.2em] text-[11px] shadow-2xl shadow-primary/30 flex items-center justify-center gap-3 active:scale-[0.98] transition-all hover:brightness-110 disabled:opacity-50"
                        >
                            {enrolling ? (
                                <><Loader2 className="animate-spin w-5 h-5" /> Encriptando...</>
                            ) : (
                                <>
                                    {step === 1 ? 'Iniciar Inscripción' : 'Confirmar Membresía'}
                                    <ArrowRight size={18} />
                                </>
                            )}
                        </button>
                        {step === 2 && (
                             <div className="flex items-center justify-center gap-2 mt-6">
                                <Lock size={12} className="text-emerald-500" />
                                <p className="text-[9px] font-black uppercase tracking-[0.1em] text-[hsl(var(--text-secondary))]">Transacción Encriptada 256-bit SSL</p>
                             </div>
                        )}
                    </div>
                )}
        </AcademyDetailShell>
    );
}
