"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LifeBuoy, Mail, MessageSquare, Phone, Clock, Send, CheckCircle, ChevronDown } from 'lucide-react';
import clsx from 'clsx';

const CHANNELS = [
    { icon: MessageSquare, label: 'Chat en Vivo', desc: 'Lun–Vie 8am–6pm', status: 'online', color: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-500/10', badge: 'En línea' },
    { icon: Mail, label: 'Correo Electrónico', desc: 'soporte@ccfaro.org', status: 'always', color: 'text-blue-500 bg-blue-50 dark:bg-blue-500/10', badge: 'Responde en 24h' },
    { icon: Phone, label: 'Línea Directa', desc: '+57 (8) 420 0000', status: 'hours', color: 'text-purple-500 bg-purple-50 dark:bg-purple-500/10', badge: 'Horario hábil' },
];

const TOPICS = ['Acceso y Cuenta', 'CRM Pastoral', 'Academia', 'Finanzas', 'Proyectos', 'Configuración', 'Reporte de Bug', 'Solicitud de Feature', 'Otro'];

export default function SupportContactPage() {
    const [submitted, setSubmitted] = useState(false);
    const [form, setForm] = useState({ name: '', email: '', topic: '', message: '', priority: 'normal' });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitted(true);
    };

    if (submitted) return (
        <div className="h-full flex flex-col items-center justify-center bg-slate-50 dark:bg-[#0f1117] space-y-5">
            <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                className="size-24 rounded-3xl bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center">
                <CheckCircle size={48} className="text-emerald-500" />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="text-center">
                <h2 className="text-xl font-black text-slate-800 dark:text-white mb-2">¡Mensaje Enviado!</h2>
                <p className="text-sm text-slate-500">Nuestro equipo te responderá en menos de 24 horas.</p>
                <p className="text-[11px] text-slate-400 mt-1">Número de caso: CCF-{Math.floor(Math.random() * 9000) + 1000}</p>
            </motion.div>
            <button onClick={() => setSubmitted(false)}
                className="px-6 py-3 bg-blue-600 text-white rounded-2xl text-sm font-black hover:bg-blue-700 transition-all shadow-lg shadow-blue-500/20">
                Enviar otra consulta
            </button>
        </div>
    );

    return (
        <div className="h-full flex flex-col bg-slate-50 dark:bg-[#0f1117]">
            <header className="h-14 border-b border-slate-200/60 dark:border-white/5 flex items-center px-6 gap-3 shrink-0 bg-white dark:bg-[#1a1d27]">
                <LifeBuoy size={16} className="text-rose-500" />
                <h1 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Contacto Directo</h1>
            </header>

            <div className="flex-1 overflow-y-auto p-8">
                <div className="max-w-3xl mx-auto space-y-8">
                    {/* Channels */}
                    <div className="grid grid-cols-3 gap-4">
                        {CHANNELS.map((ch, i) => (
                            <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                                className="bg-white dark:bg-[#1a1d27] rounded-2xl border border-slate-200/60 dark:border-white/5 p-5 shadow-sm hover:shadow-md transition-all cursor-pointer group">
                                <div className={clsx("size-11 rounded-xl flex items-center justify-center mb-3", ch.color)}>
                                    <ch.icon size={20} />
                                </div>
                                <p className="text-[13px] font-bold text-slate-700 dark:text-slate-200">{ch.label}</p>
                                <p className="text-[11px] text-slate-400 mt-0.5">{ch.desc}</p>
                                <span className={clsx("mt-3 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest", ch.color)}>
                                    <Clock size={8} /> {ch.badge}
                                </span>
                            </motion.div>
                        ))}
                    </div>

                    {/* Contact Form */}
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
                        className="bg-white dark:bg-[#1a1d27] rounded-2xl border border-slate-200/60 dark:border-white/5 p-8 shadow-sm">
                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Enviar Mensaje</p>
                        <form onSubmit={handleSubmit} className="space-y-5">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1.5">Nombre Completo</label>
                                    <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                                        placeholder="Tu nombre..."
                                        className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200/60 dark:border-white/10 rounded-xl text-sm text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 transition-all placeholder:text-slate-300" />
                                </div>
                                <div>
                                    <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1.5">Correo Electrónico</label>
                                    <input required type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                                        placeholder="correo@ejemplo.com"
                                        className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200/60 dark:border-white/10 rounded-xl text-sm text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 transition-all placeholder:text-slate-300" />
                                </div>
                            </div>

                            <div>
                                <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1.5">Tema</label>
                                <div className="relative">
                                    <select value={form.topic} onChange={e => setForm(f => ({ ...f, topic: e.target.value }))}
                                        required
                                        className="w-full appearance-none px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200/60 dark:border-white/10 rounded-xl text-sm text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 transition-all pr-10 cursor-pointer">
                                        <option value="">Seleccionar categoría...</option>
                                        {TOPICS.map(t => <option key={t} value={t}>{t}</option>)}
                                    </select>
                                    <ChevronDown size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                                </div>
                            </div>

                            <div>
                                <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1.5">Prioridad</label>
                                <div className="flex gap-3">
                                    {['normal', 'alta', 'urgente'].map(p => (
                                        <button type="button" key={p} onClick={() => setForm(f => ({ ...f, priority: p }))}
                                            className={clsx("flex-1 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest border-2 transition-all",
                                                form.priority === p ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10 text-blue-600"
                                                    : "border-slate-200 dark:border-white/5 text-slate-400 hover:border-slate-300")}>
                                            {p}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1.5">Mensaje</label>
                                <textarea required rows={5} value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                                    placeholder="Describe tu consulta o problema con el mayor detalle posible..."
                                    className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200/60 dark:border-white/10 rounded-xl text-sm text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 resize-none transition-all placeholder:text-slate-300" />
                            </div>

                            <button type="submit"
                                className="w-full flex items-center justify-center gap-2 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-black text-[12px] uppercase tracking-widest transition-all shadow-lg shadow-blue-500/20 active:scale-[0.98]">
                                <Send size={16} /> Enviar Mensaje
                            </button>
                        </form>
                    </motion.div>
                </div>
            </div>
        </div>
    );
}

