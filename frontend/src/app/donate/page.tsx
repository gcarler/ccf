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
    Lock
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
    const [completed, setCompleted] = useState(false);

    const handleDonation = async (e: React.FormEvent) => {
        e.preventDefault();
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

    if (completed) {
        return (
            <div className="min-h-screen bg-white dark:bg-[#1e1f21] flex items-center justify-center p-6">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                    className="max-w-md w-full text-center space-y-3 p-4 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/10 shadow-2xl"
                >
                    <div className="size-24 rounded-full bg-emerald-500 text-white mx-auto flex items-center justify-center shadow-lg shadow-emerald-500/20">
                        <CheckCircle2 size={48} />
                    </div>
                    <div className="space-y-3">
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white tracking-tighter">¡Ofrenda Recibida!</h2>
                        <p className="text-slate-500 dark:text-slate-400 font-medium">Tu generosidad permite que el ministerio siga creciendo y alcanzando más vidas.</p>
                    </div>
                    <div className="py-6 border-y border-slate-200 dark:border-white/10 flex justify-between items-center px-4">
                        <div className="text-left">
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Monto Sembrado</p>
                            <p className="text-lg font-bold text-slate-800 dark:text-white">${amount}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Categoría</p>
                            <p className="text-sm font-bold text-blue-600 dark:text-blue-400">{type}</p>
                        </div>
                    </div>
                    <Link href="/" className="block w-full py-5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg font-bold text-sm uppercase tracking-wide active:scale-95 transition-all shadow-xl">
                        Volver al Inicio
                    </Link>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-white dark:bg-[#1e1f21] relative overflow-hidden flex flex-col items-center">
            {/* Decorative backgrounds */}
            <div className="absolute top-0 left-0 w-full h-96 bg-gradient-to-br from-blue-600 to-indigo-900 opacity-10 dark:opacity-20 pointer-events-none" />
            <div className="absolute top-[-10%] right-[-10%] size-96 bg-blue-500 rounded-full blur-[120px] opacity-10 animate-pulse" />

            <header className="w-full max-w-5xl px-6 pt-12 flex items-center justify-between relative z-10">
                <Link href="/" className="size-12 rounded-lg bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 flex items-center justify-center text-slate-500 hover:text-blue-600 transition-all shadow-sm">
                    <ChevronLeft size={24} />
                </Link>
                <div className="flex flex-col items-center">
                    <h1 className="text-sm font-bold uppercase tracking-wide text-slate-400">Generosidad</h1>
                    <div className="h-1 w-8 bg-blue-600 rounded-full mt-1" />
                </div>
                <div className="size-12" />
            </header>

            <main className="w-full max-w-5xl px-6 py-4 grid grid-cols-1 lg:grid-cols-2 gap-3 relative z-10 items-start">
                {/* Left Side: Inspiration */}
                <div className="space-y-3 pt-4">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full text-[10px] font-bold uppercase tracking-wide">
                        <HandHeart size={14} /> Tu siembra tiene propósito
                    </div>
                    <h2 className="text-lg lg:text-xl font-bold text-slate-800 dark:text-white tracking-tighter leading-[0.9]">
                        Honramos a Dios <br /> con nuestra <br /> <span className="text-blue-600">generosidad.</span>
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
                <div className="bg-white dark:bg-[#1e1f21] rounded-lg border border-slate-100 dark:border-white/5 p-4 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.1)] dark:shadow-black/50 space-y-3">
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
                                        "py-4 rounded-lg font-bold text-sm transition-all",
                                        amount === val && !isCustom 
                                            ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30 scale-105" 
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
                                "w-full py-4 rounded-lg font-bold text-[10px] uppercase tracking-wide transition-all border-2",
                                isCustom ? "border-blue-600 bg-blue-50/50 dark:bg-blue-500/10 text-blue-600" : "border-transparent bg-slate-50 dark:bg-white/5 text-slate-400"
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

                    {/* Submit */}
                    <button 
                        onClick={handleDonation}
                        disabled={loading || !amount || parseFloat(amount) <= 0}
                        className="w-full py-6 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg font-bold text-sm uppercase tracking-wide shadow-2xl active:scale-[0.98] transition-all flex items-center justify-center gap-3 disabled:opacity-50"
                    >
                        {loading ? <Loader2 size={24} className="animate-spin" /> : <><CreditCard size={20} /> Continuar al Pago</>}
                    </button>

                    <div className="flex items-center justify-center gap-4 pt-4 border-t border-slate-50 dark:border-white/5 opacity-40">
                        <div className="flex items-center gap-1"><Lock size={12} /><span className="text-[9px] font-black uppercase">Secure SSL</span></div>
                        <div className="flex items-center gap-1"><CheckCircle2 size={12} /><span className="text-[9px] font-black uppercase">Verified Merchant</span></div>
                    </div>
                </div>
            </main>
        </div>
    );
}

function BenefitCard({ icon: Icon, title, desc }: any) {
    return (
        <div className="flex items-start gap-4 group">
            <div className="size-10 rounded-xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 shrink-0 group-hover:scale-110 transition-transform shadow-sm">
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
                "size-10 rounded-xl flex items-center justify-center transition-all",
                active ? "bg-blue-600 text-white shadow-lg" : "bg-slate-50 dark:bg-white/5 text-slate-400"
            )}>
                <Icon size={20} />
            </div>
            <span className={clsx("text-[10px] font-bold uppercase tracking-wide", active ? "text-blue-600 dark:text-white" : "text-slate-500")}>{label}</span>
        </button>
    );
}

function Loader2({ size, className }: any) { return <Sparkles size={size} className={className} />; } // Simplified fallback

