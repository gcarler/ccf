"use client";

import React, { useState } from 'react';
import { 
    BookOpen, 
    Users, 
    Heart, 
    Bell, 
    ArrowRight, 
    ChevronLeft, 
    Check, 
    Sparkles, 
    ShieldCheck, 
    MapPin, 
    Smartphone,
    UserCircle,
    Globe,
    Zap,
    Layout,
    CheckCircle2
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Image from 'next/image';

const CAMPUSES = [
    { id: 'central', name: 'Sede Central', location: 'Mocoa', color: 'from-blue-600 to-indigo-700' },
    { id: 'norte', name: 'Sede Norte', location: 'Villagarzón', color: 'from-emerald-600 to-teal-700' },
    { id: 'sur', name: 'Sede Sur', location: 'Puerto Asís', color: 'from-rose-600 to-pink-700' },
];

export default function OnboardingPage() {
    const [step, setStep] = useState(1);
    const [selectedCampus, setSelectedCampus] = useState('central');
    const [notificationsOn, setNotificationsOn] = useState(true);
    const router = useRouter();

    const nextStep = () => setStep(prev => prev + 1);
    const prevStep = () => setStep(prev => prev - 1);

    return (
        <div className="min-h-screen bg-white dark:bg-[#1e1f21] flex flex-col items-center justify-center p-6 lg:p-12 overflow-hidden relative">
            {/* Background Orbs */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none opacity-20 dark:opacity-40">
                <div className="absolute top-[-10%] left-[-10%] size-96 bg-blue-500 rounded-full blur-[120px] animate-pulse" />
                <div className="absolute bottom-[-10%] right-[-10%] size-96 bg-purple-500 rounded-full blur-[120px] animate-pulse delay-700" />
            </div>

            {/* Stepper Indicator */}
            <div className="relative z-10 w-full max-w-sm mb-12">
                <div className="flex justify-between items-center relative">
                    <div className="absolute top-1/2 left-0 w-full h-0.5 bg-slate-100 dark:bg-white/5 -translate-y-1/2 z-0" />
                    {[1, 2, 3].map((s) => (
                        <div 
                            key={s} 
                            className={clsx(
                                "size-8 rounded-full flex items-center justify-center text-[12px] font-black z-10 transition-all duration-500",
                                step >= s 
                                    ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30 scale-110" 
                                    : "bg-slate-50 dark:bg-white/5 text-slate-400 border border-slate-200 dark:border-white/5"
                            )}
                        >
                            {step > s ? <Check size={14} strokeWidth={3} /> : s}
                        </div>
                    ))}
                </div>
            </div>

            <main className="relative z-10 w-full max-w-2xl bg-white dark:bg-[#1e1f21] rounded-[2.5rem] p-8 lg:p-16 shadow-2xl border border-slate-100 dark:border-white/5 overflow-hidden">
                <AnimatePresence mode="wait">
                    {step === 1 && (
                        <motion.div 
                            key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                            className="space-y-10"
                        >
                            <div className="text-center space-y-4">
                                <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full text-[10px] font-black uppercase tracking-widest">
                                    <Sparkles size={14} /> Bienvenido a la Familia
                                </div>
                                <h1 className="text-4xl lg:text-5xl font-black text-slate-800 dark:text-white tracking-tighter leading-tight">
                                    Tu viaje espiritual <br /> comienza aquí
                                </h1>
                                <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-md mx-auto">
                                    Hemos diseñado este espacio para acompañarte en tu crecimiento y servicio.
                                </p>
                            </div>

                            <div className="grid grid-cols-1 gap-4">
                                <FeatureItem icon={BookOpen} title="Academia Faro" desc="Formación teológica formal y no formal a tu ritmo." />
                                <FeatureItem icon={Users} title="Grupos de Vida" desc="Conéctate con una comunidad cerca de tu hogar." />
                                <FeatureItem icon={Zap} title="Propósito" desc="Encuentra tu lugar de servicio en el ministerio." />
                            </div>

                            <button 
                                onClick={nextStep}
                                className="w-full py-5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-3xl font-black text-sm uppercase tracking-widest shadow-xl active:scale-95 transition-all flex items-center justify-center gap-3"
                            >
                                Empezar Experiencia <ArrowRight size={18} />
                            </button>
                        </motion.div>
                    )}

                    {step === 2 && (
                        <motion.div 
                            key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                            className="space-y-10"
                        >
                            <div className="text-center space-y-4">
                                <h2 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight">¿En qué sede te encuentras?</h2>
                                <p className="text-slate-500 dark:text-slate-400 font-medium">Elige tu comunidad local para personalizar tu dashboard.</p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {CAMPUSES.map((campus) => (
                                    <div 
                                        key={campus.id}
                                        onClick={() => setSelectedCampus(campus.id)}
                                        className={clsx(
                                            "p-6 rounded-[2rem] border-2 cursor-pointer transition-all flex flex-col items-center gap-4 group relative overflow-hidden",
                                            selectedCampus === campus.id 
                                                ? "border-blue-600 bg-blue-50/50 dark:bg-blue-500/10 shadow-lg" 
                                                : "border-slate-100 dark:border-white/5 hover:border-blue-200"
                                        )}
                                    >
                                        <div className={clsx(
                                            "size-12 rounded-2xl flex items-center justify-center text-white shadow-xl bg-gradient-to-br",
                                            campus.color
                                        )}>
                                            <MapPin size={24} />
                                        </div>
                                        <div className="text-center">
                                            <p className="text-[13px] font-black text-slate-800 dark:text-white">{campus.name}</p>
                                            <p className="text-[10px] font-bold text-slate-400">{campus.location}</p>
                                        </div>
                                        {selectedCampus === campus.id && (
                                            <div className="absolute top-3 right-3 text-blue-600 dark:text-blue-400"><CheckCircle2 size={16} /></div>
                                        )}
                                    </div>
                                ))}
                            </div>

                            <div className="flex gap-4">
                                <button onClick={prevStep} className="px-8 py-5 border-2 border-slate-100 dark:border-white/5 rounded-3xl font-black text-xs uppercase tracking-widest text-slate-400 hover:text-slate-600 transition-all">Atrás</button>
                                <button onClick={nextStep} className="flex-1 py-5 bg-blue-600 text-white rounded-3xl font-black text-sm uppercase tracking-widest shadow-xl shadow-blue-500/30 active:scale-95 transition-all flex items-center justify-center gap-3">Continuar <ArrowRight size={18} /></button>
                            </div>
                        </motion.div>
                    )}

                    {step === 3 && (
                        <motion.div 
                            key="step3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
                            className="space-y-10"
                        >
                            <div className="text-center space-y-4">
                                <h2 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight">Últimos detalles</h2>
                                <p className="text-slate-500 dark:text-slate-400 font-medium">Configura cómo quieres interactuar con la plataforma.</p>
                            </div>

                            <div className="space-y-4">
                                <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/5 flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className={clsx("size-12 rounded-2xl flex items-center justify-center transition-all", notificationsOn ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-400")}><Bell size={24} /></div>
                                        <div>
                                            <h4 className="text-sm font-black uppercase tracking-widest text-slate-700 dark:text-slate-200">Notificaciones</h4>
                                            <p className="text-xs text-slate-500">Alertas de tareas y eventos.</p>
                                        </div>
                                    </div>
                                    <div onClick={() => setNotificationsOn(!notificationsOn)} className={clsx("h-7 w-12 rounded-full relative cursor-pointer transition-colors", notificationsOn ? "bg-blue-600" : "bg-slate-300 dark:bg-white/10")}>
                                        <motion.div animate={{ x: notificationsOn ? 20 : 4 }} className="absolute top-1 size-5 bg-white rounded-full shadow-sm" />
                                    </div>
                                </div>

                                <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/5 flex items-center gap-4">
                                    <div className="size-12 rounded-2xl bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600 shrink-0"><ShieldCheck size={24} /></div>
                                    <p className="text-xs text-slate-500 font-medium leading-relaxed">Al completar el onboarding, aceptas nuestros términos de servicio y la política de protección de datos espirituales.</p>
                                </div>
                            </div>

                            <div className="flex gap-4">
                                <button onClick={prevStep} className="px-8 py-5 border-2 border-slate-100 dark:border-white/5 rounded-3xl font-black text-xs uppercase tracking-widest text-slate-400 hover:text-slate-600 transition-all">Atrás</button>
                                <button 
                                    onClick={() => router.push('/academy')}
                                    className="flex-1 py-5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-3xl font-black text-sm uppercase tracking-widest shadow-2xl active:scale-95 transition-all flex items-center justify-center gap-3"
                                >
                                    ¡Listo para empezar! <CheckCircle2 size={18} />
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>

            {/* Footer / Helper */}
            <p className="relative z-10 mt-12 text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Centro Cristiano Familiar © 2026</p>
        </div>
    );
}

function FeatureItem({ icon: Icon, title, desc }: any) {
    return (
        <div className="flex items-start gap-5 p-5 bg-white dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/10 group transition-all hover:border-blue-500/30 hover:shadow-lg">
            <div className="size-12 rounded-2xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-all shadow-sm">
                <Icon size={20} />
            </div>
            <div>
                <h4 className="text-[15px] font-black text-slate-800 dark:text-white leading-tight mb-1">{title}</h4>
                <p className="text-sm text-slate-500 dark:text-slate-400 font-medium leading-relaxed">{desc}</p>
            </div>
        </div>
    );
}
