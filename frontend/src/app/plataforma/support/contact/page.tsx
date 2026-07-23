"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LifeBuoy, Mail, MessageSquare, Phone, Clock, Send, CheckCircle, ChevronDown, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';

const CHANNELS = [
    { icon: MessageSquare, label: 'Chat en Vivo', desc: 'Lun-Vie 8am-6pm', color: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-500/10', badge: 'En linea' },
    { icon: Mail, label: 'Correo Electronico', desc: 'soporte@ccf.org', color: 'text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10', badge: 'Responde en 24h' },
    { icon: Phone, label: 'Linea Directa', desc: '+57 (8) 420 0000', color: 'text-sky-500 bg-sky-50 dark:bg-sky-500/10', badge: 'Horario habil' },
];

const TOPICS = ['Acceso y Cuenta', 'CRM Pastoral', 'Academia', 'Finanzas', 'Proyectos', 'Configuracion', 'Reporte de Bug', 'Solicitud de Feature', 'Otro'];

interface CreatedTicket {
    id: number;
}

export default function SupportContactPage() {
    const { token, user: _user } = useAuth();
    const { addToast } = useToast();
    const [submitted, setSubmitted] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [ticketId, setTicketId] = useState<number | null>(null);
    const [form, setForm] = useState({ name: '', email: '', topic: '', message: '', priority: 'normal' });

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        setSubmitting(true);
        try {
            const created = await apiFetch<CreatedTicket>('/support/', {
                method: 'POST',
                token,
                body: {
                    subject: `${form.topic || 'Consulta'} - ${form.name.trim()}`,
                    description: [
                        `Nombre: ${form.name.trim()}`,
                        `Correo: ${form.email.trim()}`,
                        `Prioridad: ${form.priority}`,
                        '',
                        form.message.trim(),
                    ].join('\n'),
                },
            });
            setTicketId(created.id);
            setSubmitted(true);
        } catch (err) {
            console.error(err);
            addToast('No se pudo enviar la consulta', 'error');
        } finally {
            setSubmitting(false);
        }
    };

    const resetForm = () => {
        setSubmitted(false);
        setTicketId(null);
        setForm({ name: '', email: '', topic: '', message: '', priority: 'normal' });
    };

    if (submitted) return (
        <div className="h-full flex flex-col items-center justify-center bg-[hsl(var(--surface-1))] dark:bg-[#0f1117] space-y-5">
            <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                className="size-10 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center">
                <CheckCircle size={48} className="text-emerald-500" />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="text-center">
                <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white mb-2">Mensaje Enviado</h2>
                <p className="text-sm text-[hsl(var(--text-secondary))]">Nuestro equipo te respondera en menos de 24 horas.</p>
                <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1">Numero de caso: CCF-{ticketId}</p>
            </motion.div>
            <button onClick={resetForm}
                className="px-3 py-3 bg-[hsl(var(--primary))] text-white rounded-lg text-sm font-semibold hover:bg-[hsl(var(--primary))] transition-all shadow-lg shadow-blue-500/20">
                Enviar otra consulta
            </button>
        </div>
    );

    return (
        <div className="h-full flex flex-col bg-[hsl(var(--surface-1))] dark:bg-[#0f1117]">
            <header className="h-8 border-b border-[hsl(var(--border))]/60 dark:border-white/5 flex items-center px-3 gap-3 shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27]">
                <LifeBuoy size={16} className="text-rose-500" />
                <h1 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Contacto Directo</h1>
            </header>

            <div className="flex-1 overflow-y-auto p-4">
                <div className="max-w-3xl mx-auto space-y-3">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                        {CHANNELS.map((channel, index) => (
                            <motion.div key={channel.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}
                                className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] rounded-lg border border-[hsl(var(--border))]/60 dark:border-white/5 p-3 shadow-sm hover:shadow-md transition-all group">
                                <div className={clsx('size-6 rounded-md flex items-center justify-center mb-3', channel.color)}>
                                    <channel.icon size={20} />
                                </div>
                                <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{channel.label}</p>
                                <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5">{channel.desc}</p>
                                <span className={clsx('mt-3 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide', channel.color)}>
                                    <Clock size={8} /> {channel.badge}
                                </span>
                            </motion.div>
                        ))}
                    </div>

                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
                        className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] rounded-lg border border-[hsl(var(--border))]/60 dark:border-white/5 p-4 shadow-sm">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Enviar Mensaje</p>
                        <form onSubmit={handleSubmit} className="space-y-5">
                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                <div>
                                    <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide block mb-1.5">Nombre Completo</label>
                                    <input required value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                                        placeholder="Tu nombre..."
                                        className="w-full px-4 py-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))]/60 dark:border-white/10 rounded-md text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] transition-all placeholder:text-[hsl(var(--text-secondary))]" />
                                </div>
                                <div>
                                    <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide block mb-1.5">Correo Electronico</label>
                                    <input required type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                                        placeholder="correo@ejemplo.com"
                                        className="w-full px-4 py-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))]/60 dark:border-white/10 rounded-md text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] transition-all placeholder:text-[hsl(var(--text-secondary))]" />
                                </div>
                            </div>

                            <div>
                                <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide block mb-1.5">Tema</label>
                                <div className="relative">
                                    <select value={form.topic} onChange={(event) => setForm((current) => ({ ...current, topic: event.target.value }))}
                                        required
                                        className="w-full appearance-none px-4 py-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))]/60 dark:border-white/10 rounded-md text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] transition-all pr-10 cursor-pointer">
                                        <option value="">Seleccionar categoria...</option>
                                        {TOPICS.map((topic) => <option key={topic} value={topic}>{topic}</option>)}
                                    </select>
                                    <ChevronDown size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] pointer-events-none" />
                                </div>
                            </div>

                            <div>
                                <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide block mb-1.5">Prioridad</label>
                                <div className="flex gap-3">
                                    {['normal', 'alta', 'urgente'].map((priority) => (
                                        <button type="button" key={priority} onClick={() => setForm((current) => ({ ...current, priority }))}
                                            className={clsx('flex-1 py-2.5 rounded-md text-[10px] font-semibold uppercase tracking-wide border-2 transition-all',
                                                form.priority === priority ? 'border-blue-500 bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))]'
                                                    : 'border-[hsl(var(--border))] dark:border-white/5 text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))]')}>
                                            {priority}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide block mb-1.5">Mensaje</label>
                                <textarea required rows={5} value={form.message} onChange={(event) => setForm((current) => ({ ...current, message: event.target.value }))}
                                    placeholder="Describe tu consulta o problema con el mayor detalle posible..."
                                    className="w-full px-4 py-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))]/60 dark:border-white/10 rounded-md text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] resize-none transition-all placeholder:text-[hsl(var(--text-secondary))]" />
                            </div>

                            <button type="submit" disabled={submitting}
                                className="w-full flex items-center justify-center gap-2 py-1.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-lg font-black text-[12px] uppercase tracking-wide transition-all shadow-lg shadow-blue-500/20 active:scale-[0.98] disabled:cursor-wait disabled:opacity-60">
                                {submitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                                {submitting ? 'Enviando...' : 'Enviar Mensaje'}
                            </button>
                        </form>
                    </motion.div>
                </div>
            </div>
        </div>
    );
}
