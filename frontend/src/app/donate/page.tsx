"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
    ChevronLeft,
    Heart,
    CreditCard,
    Smartphone,
    Building,
    ShieldCheck,
    ChevronRight,
    ArrowRight,
    Globe
} from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { useToast } from '@/context/ToastContext';

const ICON_MAP: Record<string, any> = {
    Building: Building,
    Heart: Heart,
    Globe: Globe
};

export default function DonatePage() {
    const { addToast } = useToast();
    const [amount, setAmount] = useState('50');
    const [type, setType] = useState('Diezmo');
    const [customAmount, setCustomAmount] = useState(false);
    const [loading, setLoading] = useState(false);
    const [categories, setCategories] = useState<any[]>([]);

    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const res = await fetch(apiUrl('/content/donation_types'));
                if (res.ok) {
                    const data = await res.json();
                    setCategories(JSON.parse(data.content).categories);
                }
            } catch (e) {
                console.error("Error fetching donation categories", e);
            }
        };
        fetchCategories();
    }, []);

    const handleDonation = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await fetch(apiUrl('/donations/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    amount: parseFloat(amount),
                    donation_type: type,
                    donor_name: "Anónimo"
                })
            });
            if (res.ok) {
                addToast("Ofrenda procesada con éxito. ¡Gracias!", "success");
                setAmount('50');
            }
        } catch (error) {
            addToast("Error al procesar ofrenda", "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 flex justify-center">
            <div className="w-full max-w-md relative pb-10">
                {/* Background Details */}
                <div className="absolute top-0 left-0 right-0 h-80 bg-gradient-to-br from-emerald-600 via-emerald-800 to-slate-900 rounded-b-[4rem] z-0 pointer-events-none"></div>

                {/* Header */}
                <header className="relative z-10 flex items-center justify-between px-6 pt-12 pb-6 text-white">
                    <Link href="/" className="size-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-all backdrop-blur-md">
                        <ChevronLeft size={20} />
                    </Link>
                    <h1 className="text-lg font-black tracking-widest uppercase">Ofrendas</h1>
                    <div className="size-10"></div>
                </header>

                {/* Main Content */}
                <main className="relative z-10 px-6 space-y-6">

                    {/* Amount Selector */}
                    <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-8 shadow-2xl border border-slate-100 dark:border-white/5">
                        <div className="text-center mb-8">
                            <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px] mb-2">Tu siembra</p>
                            {customAmount ? (
                                <div className="flex items-center justify-center gap-1">
                                    <span className="text-2xl font-black text-slate-400">$</span>
                                    <input
                                        type="number"
                                        value={amount}
                                        onChange={(e) => setAmount(e.target.value)}
                                        className="text-5xl font-black text-slate-900 dark:text-white bg-transparent w-32 text-center outline-none"
                                        autoFocus
                                    />
                                </div>
                            ) : (
                                <div className="flex items-center justify-center gap-1">
                                    <span className="text-2xl font-black text-slate-400">$</span>
                                    <span className="text-6xl font-black text-slate-900 dark:text-white tracking-tighter">{amount}</span>
                                </div>
                            )}
                        </div>

                        <div className="grid grid-cols-3 gap-3 mb-6">
                            {['20', '50', '100'].map((val) => (
                                <button
                                    key={val}
                                    onClick={() => { setAmount(val); setCustomAmount(false); }}
                                    className={`py-3 rounded-2xl font-black text-sm transition-all ${amount === val && !customAmount ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30' : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200'}`}
                                >
                                    ${val}
                                </button>
                            ))}
                        </div>
                        <button
                            onClick={() => setCustomAmount(true)}
                            className={`w-full py-4 rounded-2xl font-black text-xs uppercase tracking-widest transition-all ${customAmount ? 'bg-emerald-50 text-emerald-600 border border-emerald-200' : 'bg-slate-50 dark:bg-slate-800/50 text-slate-400 hover:bg-slate-100'}`}
                        >
                            Otra Cantidad
                        </button>
                    </div>

                    {/* Destination/Type */}
                    <div className="space-y-3">
                        <h3 className="font-black text-xs uppercase tracking-widest text-slate-500 ml-2">Destino</h3>
                        <div className="grid gap-3">
                            {(categories.length > 0 ? categories : [
                                { id: 'Diezmo', label: 'Diezmo', icon: 'Building' },
                                { id: 'Ofrenda General', label: 'Ofrenda General', icon: 'Heart' }
                            ]).map((item) => {
                                const Icon = ICON_MAP[item.icon] || Heart;
                                return (
                                    <button
                                        key={item.id}
                                        onClick={() => setType(item.id)}
                                        className={`w-full p-4 rounded-2xl flex items-center justify-between transition-all border ${type === item.id ? 'border-emerald-500 bg-white dark:bg-slate-900 shadow-lg' : 'border-transparent bg-white/60 dark:bg-slate-800/40 hover:bg-white'}`}
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={`size-10 rounded-xl flex items-center justify-center bg-emerald-500/10 text-emerald-500`}>
                                                <Icon size={18} />
                                            </div>
                                            <span className="font-bold text-sm">{item.label}</span>
                                        </div>
                                        <div className={`size-5 rounded-full border-2 flex items-center justify-center ${type === item.id ? 'border-emerald-500' : 'border-slate-300'}`}>
                                            {type === item.id && <div className="size-2.5 bg-emerald-500 rounded-full"></div>}
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Action Button */}
                    <button
                        onClick={handleDonation}
                        disabled={loading || !amount || parseFloat(amount) <= 0}
                        className="w-full h-16 mt-8 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-[2rem] font-black text-sm uppercase tracking-widest shadow-xl shadow-slate-900/20 flex items-center justify-center gap-3 disabled:opacity-50 transition-transform active:scale-95"
                    >
                        {loading ? 'Procesando...' : (
                            <>
                                Continuar al Pago <ArrowRight size={18} />
                            </>
                        )}
                    </button>

                    <div className="flex items-center justify-center gap-2 mt-6 opacity-60">
                        <ShieldCheck size={14} className="text-slate-400" />
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Pago 100% Seguro</span>
                    </div>

                </main>
            </div>
        </div>
    );
}

