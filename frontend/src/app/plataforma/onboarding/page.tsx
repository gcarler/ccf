"use client";

import React, { useState } from 'react';
import { 
    BookOpen, 
    Users, 
    Bell, 
    ArrowRight, 
    Check, 
    Sparkles, 
    ShieldCheck, 
    MapPin, 
    Zap,
    CheckCircle2
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const CAMPUSES = [
    { id: 'central', name: 'Sede Central', location: 'Mocoa', color: 'from-[hsl(var(--info))] to-[hsl(var(--info))]' },
    { id: 'norte', name: 'Sede Norte', location: 'Villagarzón', color: 'from-[hsl(var(--success))] to-[hsl(var(--domain-teal))]' },
    { id: 'sur', name: 'Sede Sur', location: 'Puerto Asís', color: 'from-[hsl(var(--danger))] to-[hsl(var(--domain-pink))]' },
];

export default function OnboardingPage() {
    const [step, setStep] = useState(1);
    const [selectedCampus, setSelectedCampus] = useState('central');
    const [notificationsOn, setNotificationsOn] = useState(true);
    const router = useRouter();

    const nextStep = () => setStep(prev => prev + 1);
    const prevStep = () => setStep(prev => prev - 1);

    return (
        <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] flex flex-col items-center justify-center p-3 lg:p-4 overflow-hidden relative">
            {/* Background Orbs */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none opacity-20 dark:opacity-40">
                <div className="absolute top-[-10%] left-[-10%] size-96 bg-[hsl(var(--primary))] rounded-full blur-[120px] animate-pulse" />
                <div className="absolute bottom-[-10%] right-[-10%] size-96 bg-[hsl(var(--info))] rounded-full blur-[120px] animate-pulse delay-700" />
            </div>

            {/* Stepper Indicator */}
            <div className="relative z-10 w-full max-w-sm mb-3">
                <div className="flex justify-between items-center relative">
                    <div className="absolute top-1/2 left-0 w-full h-0.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 -translate-y-1/2 z-0" />
                    {[1, 2, 3].map((s) => (
                        <div 
                            key={s} 
                            className={clsx(
                                "size-8 rounded-full flex items-center justify-center font-semibold z-10 transition-all duration-500",
                                step >= s 
                                    ? "bg-[hsl(var(--primary))] text-white shadow-lg shadow-[hsl(var(--info)/30%)] scale-110" 
                                    : "bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/5"
                            )}
                        >
                            {step > s ? <Check size={14} strokeWidth={3} /> : s}
                        </div>
                    ))}
                </div>
            </div>

            <main className="relative z-10 w-full max-w-2xl bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg p-4 lg:p-4 shadow-2xl border border-[hsl(var(--border))] dark:border-white/5 overflow-hidden">
                <AnimatePresence mode="wait">
                    {step === 1 && (
                        <motion.div 
                            key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                            className="space-y-3"
                        >
                            <div className="text-center space-y-4">
                                <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-info-soft dark:bg-[hsl(var(--info))]/30 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] rounded-full text-[10px] font-semibold uppercase tracking-wide">
                                    <Sparkles size={14} /> Bienvenido a la Familia
                                </div>
                                <h1 className="text-lg lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-tight">
                                    Tu viaje espiritual <br /> comienza aquí
                                </h1>
                                <p className="text-lg text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium max-w-md mx-auto">
                                    Hemos diseñado este espacio para acompañarte en tu crecimiento y servicio.
                                </p>
                            </div>

                            <div className="grid grid-cols-1 gap-4">
                                <FeatureItem icon={BookOpen} title="Academia CCF" desc="Formación teológica formal y no formal a tu ritmo." />
                                <FeatureItem icon={Users} title="Grupos de Vida" desc="Conéctate con una comunidad cerca de tu hogar." />
                                <FeatureItem icon={Zap} title="Propósito" desc="Encuentra tu lugar de servicio en el ministerio." />
                            </div>

                            <button 
                                onClick={nextStep}
                                className="w-full py-2 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-black text-sm uppercase tracking-wide shadow-xl active:scale-95 transition-all flex items-center justify-center gap-3"
                            >
                                Empezar Experiencia <ArrowRight size={18} />
                            </button>
                        </motion.div>
                    )}

                    {step === 2 && (
                        <motion.div 
                            key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                            className="space-y-3"
                        >
                            <div className="text-center space-y-4">
                                <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">¿En qué sede te encuentras?</h2>
                                <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium">Elige tu comunidad local para personalizar tu dashboard.</p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {CAMPUSES.map((campus) => (
                                    <div 
                                        key={campus.id}
                                        onClick={() => setSelectedCampus(campus.id)}
                                        className={clsx(
                                            "p-3 rounded-lg border-2 cursor-pointer transition-all flex flex-col items-center gap-4 group relative overflow-hidden",
                                            selectedCampus === campus.id 
                                                ? "border-[hsl(var(--info)/100%)] bg-info-soft/50 dark:bg-[hsl(var(--info))]/10 shadow-lg" 
                                                : "border-[hsl(var(--border))] dark:border-white/5 hover:border-[hsl(var(--info)/25%)]"
                                        )}
                                    >
                                        <div className={clsx(
                                            "size-7 rounded-lg flex items-center justify-center text-white shadow-xl bg-gradient-to-br",
                                            campus.color
                                        )}>
                                            <MapPin size={24} />
                                        </div>
                                        <div className="text-center">
                                            <p className="font-semibold text-[hsl(var(--text-primary))] dark:text-white">{campus.name}</p>
                                            <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">{campus.location}</p>
                                        </div>
                                        {selectedCampus === campus.id && (
                                            <div className="absolute top-3 right-3 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]"><CheckCircle2 size={16} /></div>
                                        )}
                                    </div>
                                ))}
                            </div>

                            <div className="flex gap-4">
                                <button onClick={prevStep} className="px-4 py-2 border-2 border-[hsl(var(--border))] dark:border-white/5 rounded-lg font-black text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-all">Atrás</button>
                                <button onClick={nextStep} className="flex-1 py-2 bg-[hsl(var(--primary))] text-white rounded-lg font-black text-sm uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/30%)] active:scale-95 transition-all flex items-center justify-center gap-3">Continuar <ArrowRight size={18} /></button>
                            </div>
                        </motion.div>
                    )}

                    {step === 3 && (
                        <motion.div 
                            key="step3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                            className="space-y-3"
                        >
                            <div className="text-center space-y-4">
                                <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Últimos detalles</h2>
                                <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium">Configura cómo quieres interactuar con la plataforma.</p>
                            </div>

                            <div className="space-y-4">
                                <div className="p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className={clsx("size-7 rounded-lg flex items-center justify-center transition-all", notificationsOn ? "bg-[hsl(var(--primary))] text-white" : "bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]")}><Bell size={24} /></div>
                                        <div>
                                            <h4 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Notificaciones</h4>
                                            <p className="text-xs text-[hsl(var(--text-secondary))]">Alertas de tareas y eventos.</p>
                                        </div>
                                    </div>
                                    <div onClick={() => setNotificationsOn(!notificationsOn)} className={clsx("h-7 w-12 rounded-full relative cursor-pointer transition-colors", notificationsOn ? "bg-[hsl(var(--primary))]" : "bg-[hsl(var(--surface-2))] dark:bg-white/10")}>
                                        <motion.div animate={{ x: notificationsOn ? 20 : 4 }} className="absolute top-1 size-5 bg-[hsl(var(--bg-primary))] rounded-full shadow-sm" />
                                    </div>
                                </div>

                                <div className="p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 flex items-center gap-4">
                                    <div className="size-7 rounded-lg bg-success-soft dark:bg-[hsl(var(--success))]/30 flex items-center justify-center text-success-text shrink-0"><ShieldCheck size={24} /></div>
                                    <p className="text-xs text-[hsl(var(--text-secondary))] font-medium leading-relaxed">Al completar el onboarding, aceptas nuestros términos de servicio y la política de protección de datos espirituales.</p>
                                </div>
                            </div>

                            <div className="flex gap-4">
                                <button onClick={prevStep} className="px-4 py-2 border-2 border-[hsl(var(--border))] dark:border-white/5 rounded-lg font-black text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-all">Atrás</button>
                                <button 
                                    onClick={() => router.push('/plataforma/academy')}
                                    className="flex-1 py-2 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-black text-sm uppercase tracking-wide shadow-2xl active:scale-95 transition-all flex items-center justify-center gap-3"
                                >
                                    ¡Listo para empezar! <CheckCircle2 size={18} />
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>

            {/* Footer / Helper */}
            <p className="relative z-10 mt-3 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Centro Cristiano Familiar © 2026</p>
        </div>
    );
}

function FeatureItem({ icon: Icon, title, desc }: any) {
    return (
        <div className="flex items-start gap-3 p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 group transition-all hover:border-[hsl(var(--info)/100%)]/30 hover:shadow-lg">
            <div className="size-7 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all shadow-sm">
                <Icon size={20} />
            </div>
            <div>
                <h4 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white leading-tight mb-1">{title}</h4>
                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium leading-relaxed">{desc}</p>
            </div>
        </div>
    );
}

