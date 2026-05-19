"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Heart, HeartHandshake, Mail, Phone, Globe, Youtube, Users, Podcast, Send, CheckCircle2, Wallet } from 'lucide-react';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';

export default function GivingAndConnection() {
    const { isAuthenticated, user, token } = useAuth();
    const router = useRouter();
    const { addToast } = useToast();

    const [amount, setAmount] = useState('50');
    const [isAnonymous, setIsAnonymous] = useState(false);
    const [prayerRequest, setPrayerRequest] = useState('');
    const [step, setStep] = useState(1); // 1: Hub, 2: Confirmation/Thank you
    const [isSubmitting, setIsSubmitting] = useState(false);

    if (!isAuthenticated) return null;

    const quickAmounts = ['10', '20', '50', '100'];

    const handleDonate = async () => {
        if (!amount || parseFloat(amount) <= 0) return;
        
        setIsSubmitting(true);
        try {
            await apiFetch('/donations/', {
                method: 'POST',
                token: token || undefined,
                body: {
                    amount: parseFloat(amount),
                    donation_type: 'Ofrenda General',
                    donor_name: isAnonymous ? "Anónimo" : (user?.username || "Anónimo")
                }
            });
            
            setStep(2);
            addToast('¡Gracias por tu generosidad! Tu ofrenda ha sido procesada con éxito.', 'success');
        } catch (error) {
            console.error('donation error', error);
            addToast('Error al procesar la ofrenda.', 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handlePrayerRequest = async () => {
        if (!prayerRequest.trim()) return;
        
        try {
            await apiFetch('/prayer/', {
                method: 'POST',
                token: token || undefined,
                body: {
                    name: isAnonymous ? 'Anónimo' : (user?.username || 'Anónimo'),
                    request: prayerRequest,
                    category: 'General',
                    is_anonymous: isAnonymous,
                    user_id: user?.id
                },
            });
            addToast('Tu petición de oración ha sido enviada.', 'success');
            setPrayerRequest('');
        } catch (error) {
            console.error('prayer request error', error);
            addToast('Error al enviar la petición.', 'error');
        }
    };

    if (step === 2) {
        return (
            <div className="flex flex-col items-center justify-center py-12 px-6 animate-in fade-in zoom-in-95 duration-700">
                <div className="w-24 h-24 rounded-[2.5rem] bg-[hsl(var(--primary))] flex items-center justify-center shadow-[0_20px_40px_rgba(var(--primary-rgb),0.3)] mb-8 rotate-3">
                    <CheckCircle2 size={48} className="text-white" />
                </div>

                <h1 className="text-[hsl(var(--text-primary))] text-4xl font-black text-center leading-tight mb-4 tracking-tighter">
                    Generosidad en Acción
                </h1>

                <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[3rem] p-10 max-w-lg w-full shadow-sm mb-12 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-[hsl(var(--primary)/0.05)] rounded-full blur-3xl"></div>
                    <div className="flex flex-col items-center text-center relative z-10">
                        <Heart className="text-[hsl(var(--primary))] mb-6 opacity-80" size={32} />
                        <p className="text-[hsl(var(--text-secondary))] text-xl italic leading-relaxed font-medium mb-8">
                            &quot;Cada uno dé como propuso en su corazón: no con tristeza, ni por necesidad, porque Dios ama al dador alegre.&quot;
                        </p>

                        <div className="h-0.5 w-12 bg-[hsl(var(--primary)/0.2)] mb-4"></div>
                        <p className="text-[hsl(var(--primary))] font-black tracking-[0.3em] text-[10px] uppercase">2 Corintios 9:7</p>
                    </div>
                </div>

                <div className="flex flex-col w-full max-w-xs gap-4">
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => router.push('/community/testimonies/publish')}
                        className="w-full flex items-center justify-center gap-3 bg-[hsl(var(--primary))] text-white font-black uppercase tracking-widest text-xs py-5 rounded-2xl shadow-xl shadow-primary/20 transition-all"
                    >
                        <Send size={18} />
                        Compartir Testimonio
                    </motion.button>
                    <button
                        onClick={() => setStep(1)}
                        className="w-full flex items-center justify-center gap-3 bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))] font-black uppercase tracking-widest text-xs py-5 rounded-2xl transition-all hover:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]"
                    >
                        Volver a Ofrendar
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-12 pb-20 animate-in fade-in duration-1000">
            {/* Hero Section */}
            <div className="relative overflow-hidden rounded-[3rem] bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] p-10 md:p-14 group">
                <div className="absolute top-0 right-0 -mr-16 -mt-16 bg-[hsl(var(--primary)/0.05)] size-80 rounded-full blur-[100px] transition-all duration-1000 group-hover:bg-[hsl(var(--primary)/0.1)]"></div>
                
                <div className="relative z-10 flex flex-col md:flex-row gap-10 items-center">
                    <div className="flex-1 space-y-4">
                        <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-black uppercase tracking-[0.3em] text-[10px]">
                            <div className="size-2 rounded-full bg-current shadow-[0_0_10px_currentColor]"></div>
                            Ministerio
                        </div>
                        <h1 className="text-4xl md:text-5xl font-black text-[hsl(var(--text-primary))] tracking-tighter leading-none">
                            Siembra en tierra <br/><span className="text-[hsl(var(--primary))]">Fértil</span>
                        </h1>
                        <p className="text-[hsl(var(--text-secondary))] text-lg leading-relaxed max-w-sm font-medium">
                            Tu generosidad impulsa nuestro alcance comunitario y nos ayuda a difundir el mensaje de esperanza.
                        </p>
                    </div>
                    
                    <div className="size-40 rounded-[2.5rem] bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--primary))] shadow-sm rotate-3 group-hover:rotate-6 transition-transform duration-500">
                        <HeartHandshake size={60} strokeWidth={1} />
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-10 items-start">
                {/* Donation Form */}
                <div className="lg:col-span-3 space-y-8">
                    <section className="space-y-6">
                        <h4 className="text-[hsl(var(--primary))] text-[11px] uppercase font-black tracking-[0.3em] flex items-center gap-2">
                            <div className="size-1.5 rounded-full bg-current"></div>
                            Ofrenda Voluntaria
                        </h4>

                        <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] p-10 shadow-sm space-y-8">
                            <div className="grid grid-cols-4 gap-4">
                                {quickAmounts.map((amt) => (
                                    <button
                                        key={amt}
                                        onClick={() => setAmount(amt)}
                                        className={`h-16 flex items-center justify-center rounded-2xl font-black transition-all border text-base ${amount === amt
                                            ? 'bg-[hsl(var(--primary))] text-white shadow-xl shadow-primary/30 border-transparent scale-105'
                                            : 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.4)]'
                                            }`}
                                    >
                                        ${amt}
                                    </button>
                                ))}
                            </div>

                            <div className="relative group">
                                <span className="absolute left-6 top-1/2 -translate-y-1/2 text-[hsl(var(--primary))] font-black text-3xl opacity-40 group-focus-within:opacity-100 transition-opacity">$</span>
                                <input
                                    className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-2xl py-6 pl-14 pr-6 text-[hsl(var(--text-primary))] focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] text-3xl font-black shadow-inner outline-none transition-all"
                                    placeholder="0"
                                    type="number"
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                />
                            </div>

                            <div className="space-y-4">
                                <label className="flex items-center gap-4 cursor-pointer group p-4 rounded-2xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all">
                                    <div className={`size-6 rounded-lg border-2 flex items-center justify-center transition-all ${isAnonymous ? 'bg-[hsl(var(--primary))] border-[hsl(var(--primary))] shadow-lg shadow-primary/20' : 'border-[hsl(var(--border))] group-hover:border-[hsl(var(--primary)/0.5)]'}`}>
                                        {isAnonymous && <CheckCircle2 size={14} className="text-white" />}
                                    </div>
                                    <input
                                        type="checkbox"
                                        className="hidden"
                                        checked={isAnonymous}
                                        onChange={() => setIsAnonymous(!isAnonymous)}
                                    />
                                    <div className="flex flex-col">
                                        <span className="text-xs font-black uppercase tracking-widest text-[hsl(var(--text-primary))]">Donación Anónima</span>
                                        <span className="text-[10px] text-[hsl(var(--text-secondary))] font-medium uppercase tracking-tight">Ocultar mi nombre del registro público</span>
                                    </div>
                                </label>
                            </div>

                            <motion.button
                                whileHover={{ scale: 1.01 }}
                                whileTap={{ scale: 0.99 }}
                                onClick={handleDonate}
                                disabled={isSubmitting}
                                className="w-full bg-[hsl(var(--primary))] hover:opacity-90 text-white py-6 rounded-2xl font-black uppercase tracking-[0.2em] text-xs shadow-2xl shadow-primary/20 transition-all flex items-center justify-center gap-3 border border-primary/20 disabled:opacity-50"
                            >
                                {isSubmitting ? (
                                    <div className="size-5 rounded-full border-2 border-white border-t-transparent animate-spin"></div>
                                ) : (
                                    <>
                                        <Wallet size={20} />
                                        Confirmar Ofrenda
                                    </>
                                )}
                            </motion.button>
                        </div>
                    </section>
                </div>

                {/* Connection / Prayer */}
                <div className="lg:col-span-2 space-y-8">
                    <section className="space-y-6">
                        <h4 className="text-[hsl(var(--primary))] text-[11px] uppercase font-black tracking-[0.3em] flex items-center gap-2">
                            <div className="size-1.5 rounded-full bg-current"></div>
                            Intercesión
                        </h4>

                        <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] p-8 shadow-sm space-y-6">
                            <p className="text-[hsl(var(--text-secondary))] text-xs font-semibold leading-relaxed">
                                Comparte tus peticiones con nuestro equipo. Estamos creyendo junto a ti por cada milagro.
                            </p>
                            
                            <textarea
                                className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-2xl p-5 text-[hsl(var(--text-primary))] placeholder-[hsl(var(--text-secondary)/0.5)] focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] resize-none min-h-[140px] shadow-inner text-sm font-medium outline-none transition-all"
                                placeholder="¿Cómo podemos orar por ti?"
                                value={prayerRequest}
                                onChange={(e) => setPrayerRequest(e.target.value)}
                            />

                            <button 
                                onClick={handlePrayerRequest}
                                disabled={!prayerRequest.trim()}
                                className="w-full h-14 flex items-center justify-center gap-2 bg-[hsl(var(--surface-3))] text-[hsl(var(--primary))] font-black uppercase tracking-widest text-[10px] hover:bg-[hsl(var(--primary))] hover:text-white rounded-xl transition-all border border-[hsl(var(--primary)/0.1)] disabled:opacity-50 disabled:hover:bg-[hsl(var(--surface-3))] disabled:hover:text-[hsl(var(--primary))]"
                            >
                                <span>Enviar Petición</span>
                                <Send size={14} />
                            </button>
                        </div>
                    </section>

                    {/* Contact Pills */}
                    <section className="space-y-4">
                        <div className="flex items-center gap-4 bg-[hsl(var(--surface-2))] px-6 py-5 rounded-[2rem] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-all cursor-pointer group">
                            <div className="size-10 rounded-xl bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all">
                                <Mail size={18} />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[9px] font-black uppercase tracking-widest text-[hsl(var(--text-secondary))]">Email Ministerio</span>
                                <span className="text-xs font-bold text-[hsl(var(--text-primary))]">hola@iglesiamoderna.org</span>
                            </div>
                        </div>

                        <div className="flex items-center gap-4 bg-[hsl(var(--surface-2))] px-6 py-5 rounded-[2rem] border border-[hsl(var(--border))] hover:border-emerald-500/30 transition-all cursor-pointer group">
                            <div className="size-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-500 group-hover:bg-emerald-500 group-hover:text-white transition-all">
                                <Phone size={18} />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[9px] font-black uppercase tracking-widest text-[hsl(var(--text-secondary))]">WhatsApp</span>
                                <span className="text-xs font-bold text-[hsl(var(--text-primary))]">+1 (555) 0123-456</span>
                            </div>
                        </div>
                    </section>
                </div>
            </div>

            {/* Social Hub */}
            <footer className="pt-10 flex justify-center gap-8 border-t border-[hsl(var(--border))]">
                {[Globe, Youtube, Users, Podcast].map((Icon, idx) => (
                    <motion.a 
                        key={idx} 
                        whileHover={{ y: -5, scale: 1.1 }}
                        className="text-[hsl(var(--text-secondary)/0.5)] hover:text-[hsl(var(--primary))] transition-colors cursor-pointer" 
                        href="#"
                    >
                        <Icon size={24} strokeWidth={1.5} />
                    </motion.a>
                ))}
            </footer>
        </div>
    );
}

