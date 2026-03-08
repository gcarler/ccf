"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    CreditCard,
    Smartphone,
    Banknote,
    PlusCircle,
    Edit3,
    Mail,
    FileText,
    CheckCircle2
} from 'lucide-react';

export default function DonationConfig() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [titheEnabled, setTitheEnabled] = useState(true);

    const categories = [
        { id: '1', name: 'Diezmos', color: 'bg-primary' },
        { id: '2', name: 'Misiones', color: 'bg-emerald-500' },
        { id: '3', name: 'Construcción', color: 'bg-amber-500' },
        { id: '4', name: 'Ayuda Social', color: 'bg-rose-500' },
    ];

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="px-8 pt-10 pb-6 flex items-center justify-between bg-slate-900/40 backdrop-blur-xl border-b border-white/5">
                <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-primary hover:bg-primary/10 transition-all">
                    <ArrowLeft size={20} />
                </button>
                <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-[0.1em]">Configuración de Donaciones</h1>
                <div className="w-12"></div>
            </div>

            <main className="flex-1 px-8 py-10 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700 pb-32">

                {/* Global Toggle */}
                <section className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 flex items-center justify-between shadow-2xl group hover:border-primary/30 transition-all">
                    <div>
                        <h3 className="text-lg font-black text-white tracking-tight uppercase tracking-tight">Activar Diezmo Digital</h3>
                        <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-1">Permitir aportes a través de la plataforma</p>
                    </div>
                    <button
                        onClick={() => setTitheEnabled(!titheEnabled)}
                        className={`relative w-16 h-8 rounded-full transition-all duration-500 ${titheEnabled ? 'bg-primary shadow-[0_0_15px_#259df4]' : 'bg-slate-800'}`}
                    >
                        <div className={`absolute top-1 left-1 size-6 bg-white rounded-full transition-all duration-500 shadow-lg ${titheEnabled ? 'translate-x-8' : 'translate-x-0'}`}></div>
                    </button>
                </section>

                {/* Payment Methods */}
                <section className="space-y-6">
                    <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 mb-4 ml-1">Métodos de Pago</h2>
                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] overflow-hidden shadow-2xl divide-y divide-white/5">
                        {[
                            { icon: CreditCard, label: 'Tarjeta de Crédito', enabled: true },
                            { icon: Smartphone, label: 'PayPal / Digital Wallets', enabled: true },
                            { icon: Banknote, label: 'Transferencia Bancaria', enabled: false },
                        ].map((method, idx) => (
                            <div key={idx} className="flex items-center justify-between p-6 group hover:bg-white/5 transition-all">
                                <div className="flex items-center gap-5">
                                    <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all shadow-lg">
                                        <method.icon size={24} />
                                    </div>
                                    <p className="text-sm font-black text-white tracking-tight uppercase tracking-tight">{method.label}</p>
                                </div>
                                <button className={`relative w-14 h-7 rounded-full transition-all duration-300 ${method.enabled ? 'bg-primary' : 'bg-slate-800'}`}>
                                    <div className={`absolute top-1 left-1 size-5 bg-white rounded-full transition-all duration-300 ${method.enabled ? 'translate-x-7' : 'translate-x-0'}`}></div>
                                </button>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Categories */}
                <section className="space-y-6">
                    <div className="flex items-center justify-between px-1">
                        <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600">Categorías de Ofrenda</h2>
                        <button className="text-[9px] font-black text-primary uppercase tracking-widest flex items-center gap-2 hover:underline">
                            <PlusCircle size={14} /> Nueva
                        </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {categories.map((cat) => (
                            <div key={cat.id} className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 flex items-center justify-between shadow-2xl group hover:border-white/10 transition-all">
                                <div className="flex items-center gap-4">
                                    <div className={`size-3 rounded-full ${cat.color} shadow-lg shadow-black/40 group-hover:scale-150 transition-transform`}></div>
                                    <p className="text-sm font-black text-white uppercase tracking-tight">{cat.name}</p>
                                </div>
                                <button className="text-slate-700 hover:text-primary transition-colors">
                                    <Edit3 size={18} />
                                </button>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Receipt Config */}
                <section className="space-y-6">
                    <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 mb-4 ml-1">Configuración de Recibos</h2>
                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 space-y-8 shadow-2xl">
                        <div className="flex items-center justify-between">
                            <div>
                                <h4 className="text-sm font-black text-white uppercase tracking-tight">Recibos automáticos por Email</h4>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-1">Envía un PDF al donante tras procesar el pago</p>
                            </div>
                            <button className="relative w-14 h-7 rounded-full bg-primary">
                                <div className="absolute top-1 left-1 size-5 bg-white rounded-full translate-x-7 shadow-lg"></div>
                            </button>
                        </div>
                        <div className="pt-8 border-t border-white/5">
                            <button className="w-full py-5 px-8 bg-primary/10 hover:bg-primary/20 text-primary font-black rounded-[1.5rem] border border-primary/20 transition-all flex items-center justify-center gap-4 text-[10px] uppercase tracking-[0.2em] shadow-lg shadow-primary/5 active:scale-95">
                                <FileText size={18} />
                                Personalizar Plantilla PDF
                            </button>
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}
