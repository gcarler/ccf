'use client';

import React, { useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Check, Calendar, ArrowRight, ShieldCheck, Heart } from 'lucide-react';
import { apiFetch } from '@/lib/http';

function RegisterForm() {
    const searchParams = useSearchParams();
    const eventId = searchParams?.get('event_id');

    const [form, setForm] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        accept_contact: true
    });
    
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!eventId) {
            setStatus('error');
            return;
        }

        setStatus('loading');
        try {
            await apiFetch<void>('/public/register', {
                method: 'POST',
                body: {
                    ...form,
                    event_id: parseInt(eventId, 10)
                },
                silent: true,
            });
            setStatus('success');
        } catch (err) {
            setStatus('error');
        }
    };

    if (status === 'success') {
        return (
            <div className="flex flex-col items-center justify-center text-center space-y-3 animate-in fade-in zoom-in duration-500">
                <div className="w-24 h-24 bg-[hsl(var(--success-muted))] text-success-text rounded-full flex items-center justify-center shadow-2xl shadow-[hsl(var(--success)/20%)]">
                    <Check size={48} strokeWidth={3} />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight mb-2">¡Registro Exitoso!</h2>
                    <p className="text-[hsl(var(--text-secondary))] font-medium">
                        Te hemos registrado correctamente para este evento. ¡Bienvenido a casa!
                    </p>
                </div>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-3 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {!eventId && (
                <div className="p-4 bg-danger-soft text-danger-text rounded-lg text-sm font-bold flex items-center gap-3">
                    <ShieldCheck size={20} />
                    Falta el código del evento (event_id)
                </div>
            )}
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-2">
                    <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-2">Nombres *</label>
                    <input
                        required
                        type="text"
                        value={form.first_name}
                        onChange={e => setForm({ ...form, first_name: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none font-bold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
                        placeholder="Tus nombres"
                    />
                </div>
                <div className="space-y-2">
                    <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-2">Apellidos *</label>
                    <input
                        required
                        type="text"
                        value={form.last_name}
                        onChange={e => setForm({ ...form, last_name: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none font-bold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
                        placeholder="Tus apellidos"
                    />
                </div>
            </div>

            <div className="space-y-2">
                <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-2">Correo Electrónico</label>
                <input
                    type="email"
                    value={form.email}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                    className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none font-bold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
                    placeholder="ejemplo@correo.com"
                />
            </div>

            <div className="space-y-2">
                <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-2">Teléfono móvil</label>
                <input
                    type="tel"
                    value={form.phone}
                    onChange={e => setForm({ ...form, phone: e.target.value })}
                    className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none font-bold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
                    placeholder="+57 300 000 0000"
                />
            </div>

            <div className="pt-2">
                <label className="flex items-start gap-4 cursor-pointer group">
                    <div className={`mt-1 shrink-0 w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all ${form.accept_contact ? 'bg-[hsl(var(--primary))] border-[hsl(var(--info)/100%)] text-white shadow-md shadow-[hsl(var(--info)/30%)]' : 'bg-[hsl(var(--surface-1))] border-[hsl(var(--border))]'}`}>
                        {form.accept_contact && <Check size={14} strokeWidth={4} />}
                    </div>
                    <input
                        type="checkbox"
                        checked={form.accept_contact}
                        onChange={e => setForm({ ...form, accept_contact: e.target.checked })}
                        className="hidden"
                    />
                    <span className="text-sm font-medium text-[hsl(var(--text-secondary))] leading-relaxed group-hover:text-[hsl(var(--text-primary))] transition-colors">
                        Acepto ser contactado para recibir información, material pastoral y noticias de la comunidad.
                    </span>
                </label>
            </div>

            {status === 'error' && (
                <div className="p-4 bg-danger-soft text-danger-text rounded-lg text-sm font-bold">
                    Ocurrió un error al registrar. Inténtalo de nuevo.
                </div>
            )}

            <button
                type="submit"
                disabled={status === 'loading' || !eventId}
                className="w-full py-2 bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--primary))] text-white rounded-lg text-sm font-semibold uppercase tracking-wide shadow-xl shadow-black/20 hover:shadow-[hsl(var(--info)/30%)] active:scale-[0.98] transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:hover:bg-[hsl(var(--bg-muted))]"
            >
                {status === 'loading' ? 'Registrando...' : 'Confirmar Registro'}
                {status !== 'loading' && <ArrowRight size={18} />}
            </button>
        </form>
    );
}

export default function PublicRegistrationPage() {
    return (
        <div className="min-h-screen bg-[hsl(var(--surface-1))] flex items-center justify-center p-3 sm:p-4 relative overflow-hidden">
            {/* Background Decorations */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[hsl(var(--info-muted))]/50 blur-[120px] rounded-full mix-blend-multiply pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[hsl(var(--info-muted))]/50 blur-[120px] rounded-full mix-blend-multiply pointer-events-none" />

            <div className="w-full max-w-xl bg-[hsl(var(--bg-primary))] rounded-lg shadow-2xl border border-[hsl(var(--border))] p-4 sm:p-4 relative z-10">
                <div className="flex flex-col items-center justify-center text-center space-y-4 mb-3">
                    <div className="w-16 h-8 bg-gradient-to-tr from-[hsl(var(--info))] to-[hsl(var(--info))] text-white rounded-lg flex items-center justify-center shadow-lg shadow-[hsl(var(--info)/30%)] rotate-3">
                        <Heart size={28} className="drop-shadow-md" />
                    </div>
                    <div>
                        <h1 className="text-lg sm:text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight">Registro de Asistencia</h1>
                        <p className="text-sm font-medium text-[hsl(var(--text-secondary))] mt-2 flex items-center justify-center gap-2">
                            <Calendar size={14} /> CCF Eventos
                        </p>
                    </div>
                </div>

                <Suspense fallback={<div className="h-48 flex items-center justify-center animate-pulse text-[hsl(var(--text-secondary))] font-bold">Cargando...</div>}>
                    <RegisterForm />
                </Suspense>
            </div>
        </div>
    );
}
