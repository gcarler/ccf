"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    CreditCard,
    Smartphone,
    Banknote,
    Plus,
    Edit3,
    Mail,
    FileText,
    CheckCircle2,
    Settings,
    ShieldCheck,
    Layout,
    DollarSign,
    Zap,
    Palette,
    ToggleLeft,
    ToggleRight
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { motion } from 'framer-motion';
import clsx from 'clsx';

export default function DonationConfig() {
    const { user, token } = useAuth();
    const router = useRouter();
    const [titheEnabled, setTitheEnabled] = useState(true);

    const categories = [
        { id: '1', name: 'Diezmos', color: 'bg-blue-500', desc: 'Aportes regulares de miembros.' },
        { id: '2', name: 'Misiones', color: 'bg-emerald-500', desc: 'Fondos para evangelismo externo.' },
        { id: '3', name: 'Construcción', color: 'bg-amber-500', desc: 'Mejoras de infraestructura.' },
        { id: '4', name: 'Ayuda Social', color: 'bg-rose-500', desc: 'Apoyo a familias necesitadas.' },
    ];

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Ajustes', icon: Settings }, { label: 'Finanzas', icon: DollarSign }, { label: 'Configuración de Recaudación', icon: ShieldCheck }]}
                viewType="grid" setViewType={() => {}}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl active:scale-95 transition-all">
                        <Zap size={14} /> Aplicar Cambios
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-[1000px] mx-auto space-y-12 relative z-10 pb-32">
                    
                    {/* Hero Config Section */}
                    <header className="space-y-4 text-center lg:text-left">
                        <div className="inline-flex items-center gap-2 text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-[0.3em] bg-blue-50 dark:bg-blue-900/20 px-3 py-1 rounded-lg">
                            <Settings size={14} /> Infraestructura de Tesorería
                        </div>
                        <h1 className="text-4xl lg:text-5xl font-black text-slate-800 dark:text-white tracking-tighter leading-none">
                            Configuración de <span className="text-blue-600">Recaudación.</span>
                        </h1>
                        <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-2xl">Controla los canales de entrada, categorías y automatización de recibos.</p>
                    </header>

                    {/* Master Switch */}
                    <section className="p-8 bg-slate-900 rounded-[2.5rem] text-white shadow-2xl relative overflow-hidden group border border-white/5 flex items-center justify-between">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/10 rounded-full blur-[100px]" />
                        <div className="relative z-10 space-y-2">
                            <h3 className="text-xl font-black tracking-tight uppercase tracking-tight">Activar Diezmo Digital</h3>
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Habilitar pasarela de pagos para toda la plataforma operativa.</p>
                        </div>
                        <button
                            onClick={() => setTitheEnabled(!titheEnabled)}
                            className={clsx(
                                "relative w-16 h-8 rounded-full transition-all duration-500 z-10",
                                titheEnabled ? 'bg-blue-600 shadow-[0_0_20px_rgba(37,99,235,0.5)]' : 'bg-slate-800'
                            )}
                        >
                            <motion.div 
                                animate={{ x: titheEnabled ? 32 : 4 }}
                                className="absolute top-1 size-6 bg-white rounded-full shadow-lg"
                            />
                        </button>
                    </section>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        {/* Payment Channels */}
                        <section className="space-y-6">
                            <h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 px-4">Canales de Pago</h2>
                            <div className="bg-slate-50 dark:bg-black/20 rounded-[2.5rem] border border-slate-100 dark:border-white/5 divide-y divide-slate-100 dark:divide-white/5 overflow-hidden">
                                <PaymentMethodItem icon={CreditCard} label="Tarjeta de Crédito" active />
                                <PaymentMethodItem icon={Smartphone} label="PayPal / Wallets" active />
                                <PaymentMethodItem icon={Banknote} label="Transferencia Directa" />
                            </div>
                        </section>

                        {/* Categories */}
                        <section className="space-y-6">
                            <div className="flex items-center justify-between px-4">
                                <h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Categorías de Destino</h2>
                                <button className="text-[10px] font-black text-blue-600 uppercase tracking-widest flex items-center gap-1.5 hover:underline"><Plus size={14} /> Nueva</button>
                            </div>
                            <div className="grid grid-cols-1 gap-3">
                                {categories.map((cat) => (
                                    <div key={cat.id} className="p-5 bg-white dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/30 transition-all">
                                        <div className="flex items-center gap-4">
                                            <div className={clsx("size-3 rounded-full shadow-lg transition-transform group-hover:scale-125", cat.color)} />
                                            <div>
                                                <p className="text-[13px] font-black text-slate-800 dark:text-white uppercase tracking-tight">{cat.name}</p>
                                                <p className="text-[10px] text-slate-400 font-medium">{cat.desc}</p>
                                            </div>
                                        </div>
                                        <button className="p-2 text-slate-300 hover:text-blue-600 transition-colors"><Edit3 size={16} /></button>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>

                    {/* Automation & Receipt PDF */}
                    <section className="p-10 bg-slate-50 dark:bg-black/20 rounded-[3rem] border border-slate-100 dark:border-white/5 space-y-10 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-10 opacity-5 group-hover:opacity-10 transition-opacity"><FileText size={120} /></div>
                        <div className="flex flex-col md:flex-row items-center justify-between gap-8 relative z-10">
                            <div className="space-y-4 text-center md:text-left">
                                <div className="inline-flex items-center gap-2 px-3 py-1 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-500">Automatización</div>
                                <h3 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">Emisión de Certificados</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm font-medium max-w-sm">Envía automáticamente un PDF de agradecimiento y certificado tributario tras cada aporte validado.</p>
                            </div>
                            <div className="flex flex-col gap-3 shrink-0">
                                <button className="px-8 py-4 bg-white dark:bg-white/10 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-white rounded-2xl font-black text-[10px] uppercase tracking-widest shadow-xl hover:bg-slate-50 transition-all active:scale-95 flex items-center gap-3"><Palette size={16} /> Personalizar Plantilla</button>
                                <button className="px-8 py-4 bg-slate-900 dark:bg-blue-600 text-white rounded-2xl font-black text-[10px] uppercase tracking-widest shadow-xl hover:opacity-90 transition-all active:scale-95 flex items-center gap-3"><Mail size={16} /> Probar Envío</button>
                            </div>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
}

function PaymentMethodItem({ icon: Icon, label, active }: any) {
    return (
        <div className="flex items-center justify-between p-6 group hover:bg-white dark:hover:bg-white/5 transition-all">
            <div className="flex items-center gap-5">
                <div className={clsx(
                    "size-12 rounded-2xl flex items-center justify-center transition-all shadow-sm",
                    active ? "bg-blue-600 text-white shadow-blue-500/20" : "bg-slate-100 dark:bg-white/5 text-slate-400"
                )}>
                    <Icon size={24} />
                </div>
                <div>
                    <p className="text-[14px] font-black text-slate-800 dark:text-white uppercase tracking-tight leading-none mb-1">{label}</p>
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{active ? 'Habilitado' : 'Inactivo'}</p>
                </div>
            </div>
            <div className={clsx(
                "size-2 rounded-full",
                active ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-slate-300"
            )} />
        </div>
    );
}
