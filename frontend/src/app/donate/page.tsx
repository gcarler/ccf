"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import {
    ChevronLeft,
    Heart,
    CreditCard,
    Building,
    ShieldCheck,
    Globe,
    CheckCircle2,
    Sparkles,
    HandHeart,
    Lock,
    Loader2,
    ExternalLink,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import clsx from 'clsx';

const AMOUNTS = ['20', '50', '100', '200'];

export default function DonatePage() {
    const { user } = useAuth();
    const { addToast } = useToast();
    const [amount, setAmount] = useState('50');
    const [type, setType] = useState('Diezmo');
    const [isCustom, setIsCustom] = useState(false);
    const [loading, setLoading] = useState(false);
    const [mpLoading, setMpLoading] = useState(false);
    const [completed, setCompleted] = useState(false);
    const [paymentStatus, setPaymentStatus] = useState<string | null>(null);

    // Handle return from MercadoPago (status in URL params)
    React.useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const status = params.get('status');
        if (status === 'success') {
            setCompleted(true);
            setPaymentStatus('approved');
        } else if (status === 'failure') {
            addToast('El pago no pudo completarse. Intenta de nuevo.', 'error');
        } else if (status === 'pending') {
            addToast('Tu pago está siendo procesado.', 'warning');
            setCompleted(true);
            setPaymentStatus('pending');
        }
    }, []);

    const handleManualDonation = async () => {
        setLoading(true);
        try {
            await apiFetch('/donations/', {
                method: 'POST',
                body: {
                    amount: parseFloat(amount),
                    donation_type: type,
                    donor_name: user?.username || "Anónimo"
                }
            });
            setCompleted(true);
            addToast("¡Gracias por tu generosidad!", "success");
        } catch (error) {
            console.error(error);
            addToast("Error al procesar", "error");
        } finally {
            setLoading(false);
        }
    };

    const handleMercadoPago = async () => {
        setMpLoading(true);
        try {
            const pref = await apiFetch<{ id: string; init_point: string }>('/donations/mercadopago/create-preference', {
                method: 'POST',
                body: {
                    amount: parseFloat(amount),
                    title: type,
                    donor_name: user?.username || undefined,
                    email: user?.email || undefined,
                },
            });
            if (pref?.init_point) {
                window.location.href = pref.init_point;
            } else {
                addToast('Error al iniciar pago con MercadoPago', 'error');
            }
        } catch (error: any) {
            const detail = error?.detail?.detail || error?.message;
            addToast(detail || 'Error al conectar con MercadoPago', 'error');
        } finally {
            setMpLoading(false);
        }
    };

    if (completed) {
        const isApproved = paymentStatus === 'approved' || !paymentStatus;
        return (
            <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] flex items-center justify-center p-3">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                    className="max-w-md w-full text-center space-y-3 p-4 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/10 shadow-2xl"
                >
                    <div className={`size-10 rounded-full mx-auto flex items-center justify-center shadow-lg ${isApproved ? 'bg-emerald-500' : 'bg-amber-500'}`}>
                        {isApproved ? <CheckCircle2 size={48} /> : <Sparkles size={48} />}
                    </div>
                    <div className="space-y-3">
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white tracking-tighter">
                            {isApproved ? '¡Ofrenda Recibida!' : 'Pago Pendiente'}
                        </h2>
                        <p className="text-slate-500 dark:text-slate-400 font-medium">
                            {isApproved
                                ? 'Tu generosidad permite que el ministerio siga creciendo y alcanzando más vidas.'
                                : 'Tu pago está siendo procesado. Te notificaremos cuando se confirme.'}
                        </p>
                    </div>
                    <div className="py-2 border-y border-slate-200 dark:border-white/10 flex justify-between items-center px-4">
                        <div className="text-left">
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Monto Sembrado</p>
                            <p className="text-lg font-bold text-slate-800 dark:text-white">${amount}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Categoría</p>
                            <p className="text-sm font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">{type}</p>
                        </div>
                    </div>
                    <Link href="/" className="block w-full py-2 bg-slate-900 dark:bg-[hsl(var(--bg-primary))] text-white dark:text-slate-900 rounded-lg font-bold text-sm uppercase tracking-wide active:scale-95 transition-all shadow-xl">
                        Volver al Inicio
                    </Link>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] relative overflow-hidden flex flex-col items-center">
            {/* Decorative backgrounds */}
            <div className="absolute top-0 left-0 w-full h-96 bg-gradient-to-br from-blue-600 to-indigo-900 opacity-10 dark:opacity-20 pointer-events-none" />
            <div className="absolute top-[-10%] right-[-10%] size-96 bg-[hsl(var(--primary))] rounded-full blur-[120px] opacity-10 animate-pulse" />

            <header className="w-full max-w-5xl px-3 pt-12 flex items-center justify-between relative z-10">
                <Link href="/" className="size-7 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 flex items-center justify-center text-slate-500 hover:text-[hsl(var(--primary))] transition-all shadow-sm">
                    <ChevronLeft size={24} />
                </Link>
                <div className="flex flex-col items-center">
                    <h1 className="text-sm font-bold uppercase tracking-wide text-slate-400">Generosidad</h1>
                    <div className="h-1 w-8 bg-[hsl(var(--primary))] rounded-full mt-1" />
                </div>
                <div className="size-7" />
            </header>

            <main className="w-full max-w-5xl px-3 py-1.5 grid grid-cols-1 lg:grid-cols-2 gap-3 relative z-10 items-start">
                {/* Left Side: Inspiration */}
                <div className="space-y-3 pt-4">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-50 dark:bg-blue-900/30 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] rounded-full text-[10px] font-bold uppercase tracking-wide">
                        <HandHeart size={14} /> Tu siembra tiene propósito
                    </div>
                    <h2 className="text-lg lg:text-xl font-bold text-slate-800 dark:text-white tracking-tighter leading-[0.9]">
                        Honramos a Dios <br /> con nuestra <br /> <span className="text-[hsl(var(--primary))]">generosidad.</span>
                    </h2>
                    <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-md leading-relaxed">
                        Cada ofrenda y diezmo fortalece la misión de transformar vidas y comunidades a través del evangelio.
                    </p>
                    
                    <div className="grid grid-cols-1 gap-4 pt-4">
                        <BenefitCard icon={ShieldCheck} title="Seguridad Total" desc="Tus transacciones están protegidas con encriptación de nivel bancario." />
                        <BenefitCard icon={Globe} title="Impacto Global" desc="Apoyas misiones y ayuda social en toda la región." />
                    </div>
                </div>

                {/* Right Side: Action Card */}
                <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] rounded-lg border border-slate-100 dark:border-white/5 p-4 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.1)] dark:shadow-black/50 space-y-3">
                    {/* Amount Selector */}
                    <div className="space-y-3">
                        <div className="text-center">
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-4">Selecciona un monto</p>
                            <div className="flex items-center justify-center gap-2">
                                <span className="text-lg font-bold text-slate-300">$</span>
                                {isCustom ? (
                                    <input
                                        type="number" autoFocus value={amount} onChange={(e) => setAmount(e.target.value)}
                                        className="text-xl font-bold text-slate-800 dark:text-white bg-transparent w-48 text-center outline-none tracking-tighter"
                                    />
                                ) : (
                                    <span className="text-xl font-bold text-slate-800 dark:text-white tracking-tighter">{amount}</span>
                                )}
                            </div>
                        </div>

                        <div className="grid grid-cols-4 gap-3">
                            {AMOUNTS.map(val => (
                                <button 
                                    key={val} onClick={() => { setAmount(val); setIsCustom(false); }}
                                    className={clsx(
                                        "py-1.5 rounded-lg font-bold text-sm transition-all",
                                        amount === val && !isCustom 
                                            ? "bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/30 scale-105" 
                                            : "bg-slate-50 dark:bg-white/5 text-slate-500 hover:bg-slate-100"
                                    )}
                                >
                                    ${val}
                                </button>
                            ))}
                        </div>
                        <button 
                            onClick={() => setIsCustom(true)}
                            className={clsx(
                                "w-full py-1.5 rounded-lg font-bold text-[10px] uppercase tracking-wide transition-all border-2",
                                isCustom ? "border-blue-600 bg-blue-50/50 dark:bg-blue-500/10 text-[hsl(var(--primary))]" : "border-transparent bg-slate-50 dark:bg-white/5 text-slate-400"
                            )}
                        >
                            Otra cantidad personalizada
                        </button>
                    </div>

                    {/* Type Selector */}
                    <div className="space-y-4">
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide text-center">Destino de la semilla</p>
                        <div className="grid grid-cols-2 gap-3">
                            <TypeOption active={type === 'Diezmo'} onClick={() => setType('Diezmo')} icon={Building} label="Diezmo" />
                            <TypeOption active={type === 'Ofrenda'} onClick={() => setType('Ofrenda')} icon={Heart} label="Ofrenda" />
                        </div>
                    </div>

                    {/* Submit — MercadoPago */}
                    <button
                        onClick={handleMercadoPago}
                        disabled={mpLoading || !amount || parseFloat(amount) <= 0}
                        className="w-full py-2.5 bg-[hsl(var(--primary))] text-white rounded-lg font-bold text-sm uppercase tracking-wide shadow-xl shadow-blue-500/30 active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-[hsl(var(--primary))]"
                    >
                        {mpLoading ? (
                            <><Loader2 size={18} className="animate-spin" /> Conectando...</>
                        ) : (
                            <><ExternalLink size={18} /> Pagar con MercadoPago</>
                        )}
                    </button>

                    {/* Manual registration (admin only) */}
                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-slate-100 dark:border-white/5" />
                        </div>
                        <div className="relative flex justify-center">
                            <span className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] px-3 text-[9px] font-bold uppercase tracking-wide text-slate-300">
                                O registra manualmente
                            </span>
                        </div>
                    </div>

                    <button
                        onClick={handleManualDonation}
                        disabled={loading || !amount || parseFloat(amount) <= 0}
                        className="w-full py-2 bg-slate-100 dark:bg-white/5 text-slate-500 rounded-lg font-bold text-[11px] uppercase tracking-wide active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-slate-200 dark:hover:bg-white/10"
                    >
                        {loading ? <Loader2 size={16} className="animate-spin" /> : <><CreditCard size={16} /> Registrar como recibido</>}
                    </button>

                    <div className="flex items-center justify-center gap-4 pt-4 border-t border-slate-50 dark:border-white/5 opacity-40">
                        <div className="flex items-center gap-1"><Lock size={12} /><span className="text-[9px] font-semibold uppercase">Secure SSL</span></div>
                        <div className="flex items-center gap-1"><CheckCircle2 size={12} /><span className="text-[9px] font-semibold uppercase">Verified Merchant</span></div>
                    </div>
                </div>
            </main>
        </div>
    );
}

function BenefitCard({ icon: Icon, title, desc }: any) {
    return (
        <div className="flex items-start gap-4 group">
            <div className="size-10 rounded-md bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-[hsl(var(--primary))] shrink-0 group-hover:scale-110 transition-transform shadow-sm">
                <Icon size={20} />
            </div>
            <div>
                <h4 className="text-sm font-bold uppercase tracking-wide text-slate-700 dark:text-slate-200">{title}</h4>
                <p className="text-xs text-slate-500 leading-relaxed mt-0.5">{desc}</p>
            </div>
        </div>
    );
}

function TypeOption({ active, onClick, icon: Icon, label }: any) {
    return (
        <button 
            onClick={onClick}
            className={clsx(
                "p-4 rounded-lg border-2 flex flex-col items-center gap-2 transition-all group",
                active 
                    ? "border-blue-600 bg-blue-50/50 dark:bg-blue-500/10 shadow-md" 
                    : "border-slate-50 dark:border-white/5 hover:border-blue-200"
            )}
        >
            <div className={clsx(
                "size-10 rounded-md flex items-center justify-center transition-all",
                active ? "bg-[hsl(var(--primary))] text-white shadow-lg" : "bg-slate-50 dark:bg-white/5 text-slate-400"
            )}>
                <Icon size={20} />
            </div>
            <span className={clsx("text-[10px] font-bold uppercase tracking-wide", active ? "text-[hsl(var(--primary))] dark:text-white" : "text-slate-500")}>{label}</span>
        </button>
    );
}

