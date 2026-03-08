"use client";

import React, { useState, useEffect } from 'react';
import { BookOpen, Users, Heart, Bell, BellOff, ArrowRight, ChevronLeft, Check } from 'lucide-react';
import Link from 'next/link';
import { apiUrl } from '@/lib/api';

const ICON_MAP: Record<string, any> = {
    BookOpen: BookOpen,
    Users: Users,
    Heart: Heart
};

export default function OnboardingPage() {
    const [step, setStep] = useState(1);
    const [selectedCampus, setSelectedCampus] = useState('central');
    const [notificationsOn, setNotificationsOn] = useState(false);
    const [content, setContent] = useState<any>(null);

    useEffect(() => {
        const fetchContent = async () => {
            try {
                const res = await fetch(apiUrl('/content/onboarding_page'));
                if (res.ok) {
                    const data = await res.json();
                    setContent(JSON.parse(data.content));
                }
            } catch (err) {
                console.error("Error fetching onboarding content", err);
            }
        };
        fetchContent();
    }, []);

    const step1Data = content?.steps?.find((s: any) => s.id === 1) || {
        title: "Herramientas para tu fe",
        description: "Diseñamos un espacio digital para acompañarte en cada paso de tu caminar cristiano.",
        features: [
            { title: "Crecimiento", desc: "Fortalece tu espíritu...", icon: "BookOpen" },
            { title: "Comunidad", desc: "Conecta con grupos...", icon: "Users" },
            { title: "Propósito", desc: "Encuentra y sirve...", icon: "Heart" }
        ]
    };

    // Step 1: Descubre tu Camino
    if (step === 1) {
        return (
            <div className="relative flex min-h-screen w-full flex-col bg-slate-50 dark:bg-slate-950 overflow-hidden font-display">
                {/* Header / Navigation */}
                <div className="flex items-center bg-slate-50 dark:bg-slate-950 p-6 pb-2 justify-between z-10 max-w-md mx-auto w-full">
                    <h2 className="text-primary text-sm font-bold uppercase tracking-widest">Descubre tu Camino</h2>
                    <Link href="/academy" className="text-slate-400 dark:text-slate-500 text-sm font-semibold hover:text-primary transition-colors">Omitir</Link>
                </div>

                <div className="flex flex-col flex-1 max-w-md mx-auto w-full z-10">
                    {/* Hero Content */}
                    <div className="px-6 pt-10 pb-6 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <h1 className="text-slate-900 dark:text-slate-100 tracking-tight text-3xl font-extrabold leading-tight mb-3">
                            {step1Data.title}
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400 text-base leading-relaxed max-w-[280px] mx-auto">
                            {step1Data.description}
                        </p>
                    </div>

                    {/* Features Grid */}
                    <div className="flex-1 overflow-y-auto px-6 space-y-4 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                        {step1Data.features.map((feat: any, idx: number) => {
                            const Icon = ICON_MAP[feat.icon] || BookOpen;
                            return (
                                <div key={idx} className="group flex items-center gap-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 hover:border-primary/50 dark:hover:border-primary/50 transition-all duration-300 shadow-sm hover:shadow-md">
                                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary group-hover:bg-primary group-hover:text-white transition-all duration-300">
                                        <Icon className="w-6 h-6" />
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <h2 className="text-slate-900 dark:text-slate-100 text-lg font-bold leading-tight">{feat.title}</h2>
                                        <p className="text-slate-500 dark:text-slate-400 text-sm font-normal leading-relaxed">{feat.desc}</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Bottom Actions */}
                    <div className="p-6 bg-slate-50 dark:bg-slate-950 mt-auto">
                        {/* Progress Dots */}
                        <div className="flex w-full flex-row items-center justify-center gap-2.5 pb-8">
                            <div className="h-2 w-8 rounded-full bg-primary"></div>
                            <div className="h-2 w-2 rounded-full bg-slate-300 dark:bg-slate-800"></div>
                        </div>

                        {/* Primary Button */}
                        <button
                            onClick={() => setStep(2)}
                            className="flex w-full items-center justify-center rounded-xl h-14 px-5 bg-primary text-white text-base font-bold shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all active:scale-95"
                        >
                            <span>Siguiente</span>
                            <ArrowRight className="ml-2 w-5 h-5 flex-shrink-0" />
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Step 2: Personaliza tu Experiencia
    return (
        <div className="relative flex min-h-screen w-full flex-col bg-slate-50 dark:bg-slate-950 overflow-hidden font-display">
            {/* Header */}
            <div className="flex items-center px-4 py-4 justify-between max-w-lg mx-auto w-full">
                <button
                    onClick={() => setStep(1)}
                    className="flex size-10 items-center justify-center rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"
                >
                    <ChevronLeft className="w-6 h-6 pr-0.5" />
                </button>
                <h2 className="text-slate-900 dark:text-slate-100 text-base font-semibold leading-tight flex-1 text-center pr-10">Personalización</h2>
            </div>

            <div className="flex flex-col flex-1 max-w-lg mx-auto w-full z-10 w-full overflow-y-auto pb-24">
                <div className="px-6 flex flex-col items-center pt-2 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <h1 className="text-slate-900 dark:text-slate-100 text-[28px] font-bold leading-tight text-center tracking-tight">¿En qué sede te encuentras?</h1>
                    <p className="text-slate-500 dark:text-slate-400 text-sm mt-2 text-center">Elige tu comunidad local para ver eventos y liderazgos cercanos.</p>
                </div>

                {/* Horizontal Scrolling Campuses */}
                <div className="mt-8 px-4 animate-in fade-in slide-in-from-right-8 duration-700 delay-100">
                    <div className="flex overflow-x-auto gap-4 pb-6 snap-x hide-scrollbar" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>

                        {/* Campus 1 */}
                        <div
                            onClick={() => setSelectedCampus('central')}
                            className={`snap-center shrink-0 w-[200px] group relative flex flex-col gap-3 rounded-2xl overflow-hidden aspect-[4/5] cursor-pointer transition-all duration-300 ${selectedCampus === 'central' ? 'border-4 border-primary shadow-xl shadow-primary/20 scale-100' : 'border-4 border-transparent scale-95 opacity-80 hover:opacity-100'}`}
                        >
                            <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "linear-gradient(to top, rgba(15, 23, 42, 0.95) 0%, rgba(15, 23, 42, 0.2) 50%, transparent 100%), url('https://lh3.googleusercontent.com/aida-public/AB6AXuAR89hqrGixgDo5gyAtEPJsXa4CXjRBdyuHElcJMkLKSXVPDJpAaK9seRqocRisjlh3c3QFunADv1tXzyBnOihU7z2r9Ehm321-QVeL8JVAzeYC3kZJ7UJ47FOoXBg6kM7pKUrv1zk-nK-yuxmfgbuKmHeYReN9livUS1nHXvbhfHLkU1ILfvStk4aU9aklJxVu-dDswb0fLZXfJni9jr-TJOgF4FGcsHYqNBQBqz0vZMoePd8SrfFRdoSeHWacr2VddquWUvmM0eU')" }}></div>
                            <div className="mt-auto p-5 z-10">
                                <p className="text-white text-xl font-black">Sede Central</p>
                                <p className="text-primary-300 text-sm font-semibold opacity-90">Ciudad de Mocoa</p>
                            </div>
                            {selectedCampus === 'central' && (
                                <div className="absolute top-4 right-4 z-10 bg-primary rounded-full p-1.5 shadow-lg">
                                    <Check className="text-white w-4 h-4" strokeWidth={3} />
                                </div>
                            )}
                        </div>

                        {/* Campus 2 */}
                        <div
                            onClick={() => setSelectedCampus('norte')}
                            className={`snap-center shrink-0 w-[200px] group relative flex flex-col gap-3 rounded-2xl overflow-hidden aspect-[4/5] cursor-pointer transition-all duration-300 ${selectedCampus === 'norte' ? 'border-4 border-primary shadow-xl shadow-primary/20 scale-100' : 'border-4 border-transparent scale-95 opacity-80 hover:opacity-100'}`}
                        >
                            <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "linear-gradient(to top, rgba(15, 23, 42, 0.95) 0%, rgba(15, 23, 42, 0.2) 50%, transparent 100%), url('https://lh3.googleusercontent.com/aida-public/AB6AXuCgq9kmuTh-8XtJWTfpxffjssttOPON3V_q0-rPDEqC4AsyAI6yDvDPT82LLR6JBu7RJQhSrRapSIua6UWn00AGGHl3H-6jbR1-2TUFzKiCVwyQDT1gWOQNr8-uWfUsJxPEXd-vqpZFl8wKTRqsMjlRyNoXpgAUA5o1HTXrIi5Da38o4kgf_-vQfTUBWNUzwUzfNIrf1BLwPR8TBwK_EujlKSCmzymYnGI5Slzrjf7ETqfFZVpwnrCTO1JLrZe4EZizOmy86Avs_5s')" }}></div>
                            <div className="mt-auto p-5 z-10">
                                <p className="text-white text-xl font-black">Sede Norte</p>
                                <p className="text-slate-300 text-sm font-semibold opacity-90">Villagarzón</p>
                            </div>
                            {selectedCampus === 'norte' && (
                                <div className="absolute top-4 right-4 z-10 bg-primary rounded-full p-1.5 shadow-lg">
                                    <Check className="text-white w-4 h-4" strokeWidth={3} />
                                </div>
                            )}
                        </div>

                        {/* Campus 3 */}
                        <div
                            onClick={() => setSelectedCampus('sur')}
                            className={`snap-center shrink-0 w-[200px] group relative flex flex-col gap-3 rounded-2xl overflow-hidden aspect-[4/5] cursor-pointer transition-all duration-300 pr-4 ${selectedCampus === 'sur' ? 'border-4 border-primary shadow-xl shadow-primary/20 scale-100' : 'border-4 border-transparent scale-95 opacity-80 hover:opacity-100'}`}
                        >
                            <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "linear-gradient(to top, rgba(15, 23, 42, 0.95) 0%, rgba(15, 23, 42, 0.2) 50%, transparent 100%), url('https://lh3.googleusercontent.com/aida-public/AB6AXuBHn08qY8p4hnaioqr8hNs3umIftMF8z23KAHCUsKwkbbKMhhnhjuOZr9zrtDopeH2724aDe_O2Qo11cSLhAZoG40R70sjQzW8bQZQYQaevqijP7suvwfz0mXl84HB9eeHHTuo9yvw1sTd5yb0PbE6XP7EK5L1RDnqd6hUUiWrarlXvHwtJm86VRjgJh8k8BG5mRnW23pebr5jFOvchXjMu3xMQmMG1YywTRkiUlcTnabbOu2GHomO4BDTHTex0n0QZxzmZDacHHYw')" }}></div>
                            <div className="mt-auto p-5 z-10">
                                <p className="text-white text-xl font-black">Sede Sur</p>
                                <p className="text-slate-300 text-sm font-semibold opacity-90">Puerto Asís</p>
                            </div>
                            {selectedCampus === 'sur' && (
                                <div className="absolute top-4 right-4 z-10 bg-primary rounded-full p-1.5 shadow-lg">
                                    <Check className="text-white w-4 h-4" strokeWidth={3} />
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="px-6 mt-4 flex-1 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
                    <div className="bg-primary/5 dark:bg-primary/10 rounded-2xl border border-primary/20 p-5 flex items-center justify-between shadow-sm">
                        <div className="flex items-center gap-4">
                            <div className={`size-12 rounded-full flex items-center justify-center transition-colors ${notificationsOn ? 'bg-primary text-white' : 'bg-primary/20 text-primary'}`}>
                                {notificationsOn ? <Bell className="w-5 h-5" /> : <BellOff className="w-5 h-5" />}
                            </div>
                            <div>
                                <h3 className="text-slate-900 dark:text-slate-100 font-bold text-base leading-tight">Mantente conectado</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">Activar Notificaciones</p>
                            </div>
                        </div>
                        {/* iOS Style Toggle Switch */}
                        <div
                            onClick={() => setNotificationsOn(!notificationsOn)}
                            className={`relative inline-flex h-7 w-12 items-center rounded-full cursor-pointer transition-colors duration-300 ${notificationsOn ? 'bg-primary' : 'bg-slate-300 dark:bg-slate-700'}`}
                        >
                            <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition-transform duration-300 ${notificationsOn ? 'translate-x-6' : 'translate-x-1'}`}></span>
                        </div>
                    </div>

                    <div className="mt-6 flex flex-col gap-3">
                        <div className="flex items-center gap-3 px-2 py-1 bg-emerald-50 dark:bg-emerald-500/10 rounded-xl p-4">
                            <div className="bg-emerald-100 dark:bg-emerald-500/20 p-2 rounded-lg text-emerald-600 dark:text-emerald-400">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>
                            </div>
                            <p className="text-slate-700 dark:text-slate-300 text-sm font-medium">Tu privacidad es nuestra prioridad espiritual.</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="p-6 bg-slate-50 dark:bg-slate-950 fixed w-full bottom-0 z-20 max-w-lg mx-auto left-0 right-0 border-t border-slate-200 dark:border-slate-800">
                {/* Progress Dots */}
                <div className="flex w-full flex-row items-center justify-center gap-2.5 pb-6">
                    <div className="h-2 w-2 rounded-full bg-slate-300 dark:bg-slate-800" onClick={() => setStep(1)} style={{ cursor: 'pointer' }}></div>
                    <div className="h-2 w-8 rounded-full bg-primary shadow-[0_0_8px_rgba(66,66,240,0.4)]"></div>
                </div>

                <Link href="/academy" className="w-full h-14 bg-primary hover:bg-primary/90 text-white font-bold py-4 rounded-xl shadow-[0_0_20px_rgba(66,66,240,0.3)] flex items-center justify-center gap-2 transition-all active:scale-95">
                    Ir al Inicio
                    <ArrowRight className="w-5 h-5" />
                </Link>
            </div>

            <style jsx global>{`
                .hide-scrollbar::-webkit-scrollbar {
                    display: none;
                }
            `}</style>
        </div>
    );
}
