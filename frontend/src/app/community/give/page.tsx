"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Heart, HeartHandshake, Mail, Phone, Globe, Youtube, Users, Podcast, Send, CheckCircle2, CreditCard, Wallet, Coins } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

export default function GivingAndConnection() {
    const { isAuthenticated, user } = useAuth();
    const router = useRouter();
    const { addToast } = useToast();

    const [amount, setAmount] = useState('50');
    const [isAnonymous, setIsAnonymous] = useState(false);
    const [prayerRequest, setPrayerRequest] = useState('');
    const [step, setStep] = useState(1); // 1: Hub, 2: Confirmation/Thank you

    if (!isAuthenticated) return null;

    const quickAmounts = ['10', '20', '50', '100'];

    const handleDonate = () => {
        if (!amount || parseFloat(amount) <= 0) return;
        setStep(2);
        addToast('¡Gracias por tu generosidad! Tu ofrenda ha sido procesada con éxito.', 'success');


        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    if (step === 2) {
        return (
            <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-hidden flex flex-col items-center justify-center px-6">
                <div className="absolute top-0 left-0 w-full h-1/2 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/20 via-slate-950 to-slate-950"></div>

                <div className="relative z-10 flex flex-col items-center max-w-md w-full animate-in fade-in zoom-in-95 duration-700">
                    <div className="w-24 h-24 rounded-full bg-primary flex items-center justify-center shadow-[0_0_40px_rgba(66,66,240,0.6)] ring-8 ring-primary/10 mb-8">
                        <CheckCircle2 size={48} className="text-white" />
                    </div>

                    <h1 className="text-white text-3xl font-black text-center leading-tight mb-4 tracking-tight">
                        ¡Gracias por tu generosidad!
                    </h1>

                    <div className="bg-slate-900/60 backdrop-blur-xl border border-white/10 rounded-[2rem] p-8 shadow-2xl mb-10 w-full">
                        <div className="flex flex-col items-center text-center">
                            <Heart className="text-primary mb-5 opacity-70 animate-pulse" size={32} />
                            <p className="text-slate-300 text-lg italic leading-relaxed font-medium mb-6">
                                &quot;Cada uno dé como propuso en su corazón: no con tristeza, ni por necesidad, porque Dios ama al dador alegre.&quot;
                            </p>

                            <div className="h-px w-16 bg-primary/30 mb-5"></div>
                            <p className="text-primary font-black tracking-[0.2em] text-[10px] uppercase">2 Corintios 9:7</p>
                        </div>
                    </div>

                    <div className="w-full space-y-4">
                        <button
                            onClick={() => router.push('/community/testimonies/publish')}
                            className="w-full flex items-center justify-center gap-3 bg-primary hover:bg-primary-600 text-white font-black uppercase tracking-widest text-xs py-4 rounded-2xl shadow-xl shadow-primary/30 transition-all active:scale-95 border border-primary-400/20"
                        >
                            <Send size={18} />
                            Compartir Testimonio
                        </button>
                        <button
                            onClick={() => setStep(1)}
                            className="w-full flex items-center justify-center gap-3 bg-white/5 hover:bg-white/10 text-slate-300 font-black uppercase tracking-widest text-xs py-4 rounded-2xl transition-all active:scale-95 border border-white/5"
                        >
                            Volver
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/15 via-slate-950 to-slate-950 opacity-60 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 py-4 border-b border-white/5 flex items-center justify-between">
                    <button onClick={() => router.back()} className="text-slate-400 flex size-10 items-center justify-center rounded-full bg-white/5 hover:bg-primary/20 hover:text-primary transition-all cursor-pointer">
                        <ArrowLeft size={20} />
                    </button>
                    <h2 className="text-white text-lg font-black tracking-tight flex-1 text-center pr-10">Ofrendas y Conexión</h2>
                </header>

                <main className="flex-1 pb-32 overflow-y-auto hide-scrollbar pt-6 px-6 space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">

                    {/* Hero Card */}
                    <div className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-primary via-primary-600 to-indigo-800 p-8 text-white shadow-2xl shadow-primary/30 group">
                        <div className="absolute top-0 right-0 -mr-16 -mt-16 bg-white/10 size-64 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-1000"></div>
                        <div className="relative z-10">
                            <h3 className="text-3xl font-black mb-3 tracking-tight">Apoya al Ministerio</h3>
                            <p className="text-white/80 text-sm leading-relaxed max-w-sm font-medium">Tu generosidad impulsa nuestro alcance comunitario y nos ayuda a difundir el mensaje de esperanza en todo el mundo.</p>
                        </div>
                    </div>

                    {/* Tithes & Offerings Section */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-3">
                            <div className="size-8 rounded-full bg-primary/10 flex items-center justify-center text-primary shadow-inner border border-primary/20">
                                <HeartHandshake size={16} />
                            </div>
                            <h3 className="text-white text-xl font-black tracking-tight">Diezmos y Ofrendas</h3>
                        </div>

                        <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 shadow-xl">
                            <div className="grid grid-cols-4 gap-3 mb-6">
                                {quickAmounts.map((amt) => (
                                    <button
                                        key={amt}
                                        onClick={() => setAmount(amt)}
                                        className={`flex h-14 items-center justify-center rounded-2xl font-black transition-all border text-sm ${amount === amt
                                            ? 'bg-primary text-white shadow-lg shadow-primary/30 border-primary-400/50 scale-105'
                                            : 'bg-white/5 text-slate-400 border-white/5 hover:border-white/20'
                                            }`}
                                    >
                                        ${amt}
                                    </button>
                                ))}
                            </div>

                            <div className="relative group mb-6">
                                <span className="absolute left-5 top-1/2 -translate-y-1/2 text-primary font-black text-2xl group-focus-within:scale-110 transition-transform">$</span>
                                <input
                                    className="w-full bg-slate-950/50 border border-white/10 rounded-2xl py-5 pl-12 pr-6 text-white focus:ring-2 focus:ring-primary/50 focus:border-primary/50 text-2xl font-black shadow-inner"
                                    placeholder="0"
                                    type="number"
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                />
                            </div>

                            <button
                                onClick={handleDonate}
                                className="w-full bg-primary hover:bg-primary-600 text-white py-5 rounded-2xl font-black uppercase tracking-[0.2em] text-xs shadow-2xl shadow-primary/40 active:scale-95 transition-all flex items-center justify-center gap-3 border border-primary-400/20"
                            >
                                <Wallet size={18} />
                                Ofrendar Ahora
                            </button>
                        </div>
                    </section>

                    {/* Prayer Request Section */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-3">
                            <div className="size-8 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-400 shadow-inner border border-indigo-500/20">
                                <Send size={16} />
                            </div>
                            <h3 className="text-white text-xl font-black tracking-tight">Petición de Oración</h3>
                        </div>
                        <p className="text-slate-500 text-sm font-medium pl-1">Comparte tus peticiones con nuestro equipo de intercesión. Estamos creyendo junto a ti.</p>

                        <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 shadow-xl">
                            <textarea
                                className="w-full bg-slate-950/50 border border-white/10 rounded-2xl p-5 text-white placeholder-slate-600 focus:ring-2 focus:ring-primary/50 focus:border-primary/50 resize-none min-h-[120px] shadow-inner mb-6 transition-all"
                                placeholder="¿Cómo podemos orar por ti?"
                                value={prayerRequest}
                                onChange={(e) => setPrayerRequest(e.target.value)}
                            />

                            <div className="flex items-center justify-between">
                                <label className="flex items-center gap-3 cursor-pointer group">
                                    <div className={`size-6 rounded-lg border-2 flex items-center justify-center transition-all ${isAnonymous ? 'bg-primary border-primary shadow-lg shadow-primary/20' : 'border-white/10 group-hover:border-white/30'}`}>
                                        {isAnonymous && <CheckCircle2 size={14} className="text-white" />}
                                    </div>
                                    <input
                                        type="checkbox"
                                        className="hidden"
                                        checked={isAnonymous}
                                        onChange={() => setIsAnonymous(!isAnonymous)}
                                    />
                                    <span className="text-[11px] font-black uppercase tracking-widest text-slate-500 group-hover:text-slate-300 transition-colors">Publicar anónimo</span>
                                </label>

                                <button className="flex items-center gap-2 text-primary font-black uppercase tracking-widest text-[11px] hover:text-primary-400 transition-colors">
                                    <span>Enviar</span>
                                    <Send size={14} className="translate-y-[-1px]" />
                                </button>
                            </div>
                        </div>
                    </section>

                    {/* Contact Info Section */}
                    <section className="bg-slate-900/20 backdrop-blur-sm rounded-[2.5rem] border border-white/5 p-10 text-center space-y-8 mb-20">
                        <h4 className="text-lg font-black tracking-tight text-white mb-6 uppercase tracking-[0.2em]">Ponte en Contacto</h4>

                        <div className="flex flex-col md:flex-row items-center justify-center gap-6">
                            <div className="flex items-center gap-4 bg-white/5 px-6 py-4 rounded-2xl border border-white/5 hover:border-primary/30 transition-all cursor-pointer group">
                                <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all">
                                    <Mail size={18} />
                                </div>
                                <span className="text-sm font-bold text-slate-300">hola@iglesiamoderna.org</span>
                            </div>
                            <div className="flex items-center gap-4 bg-white/5 px-6 py-4 rounded-2xl border border-white/5 hover:border-emerald-500/30 transition-all cursor-pointer group">
                                <div className="size-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:bg-emerald-500 group-hover:text-white transition-all">
                                    <Phone size={18} />
                                </div>
                                <span className="text-sm font-bold text-slate-300">+1 (555) 0123-456</span>
                            </div>
                        </div>

                        <div className="flex justify-center gap-8 pt-4">
                            {[Globe, Youtube, Users, Podcast].map((Icon, idx) => (
                                <a key={idx} className="text-slate-600 hover:text-primary transition-all hover:scale-125 duration-300 cursor-pointer" href="#">
                                    <Icon size={24} />
                                </a>
                            ))}
                        </div>
                    </section>
                </main>
            </div>
        </div>
    );
}
