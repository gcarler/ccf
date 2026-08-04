'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Calendar, MapPin, Clock, Check, X, QrCode, Mail, Loader2, ShieldCheck, ArrowRight, Users, AlertTriangle } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { apiFetch, ApiError } from '@/lib/http';

type PublicEventInfo = {
    id: string;
    name: string;
    description: string | null;
    event_date: string | null;
    start_time: string | null;
    end_time: string | null;
    location: string | null;
    event_type: string;
    requires_registration: boolean;
    requires_email_verification: boolean;
    capacity_max: number | null;
    waiting_list_enabled: boolean;
    registration_opens_at: string | null;
    registration_closes_at: string | null;
    contact_person: string | null;
    is_open: boolean;
    capacity_remaining: number | null;
};

type RegistrationStatus =
    | 'PENDING'
    | 'CONFIRMED'
    | 'CHECKED_IN'
    | 'ABSENT'
    | 'CANCELLED'
    | 'WAITLIST';

type RegistrationResult = {
    id: string;
    event_id: string;
    persona_id: string;
    persona_name: string | null;
    persona_email: string | null;
    persona_phone: string | null;
    registration_status: RegistrationStatus;
    qr_token: string | null;
    qr_generated_at: string | null;
    registered_at: string;
    confirmed_at: string | null;
    cancelled_at: string | null;
    check_in_at: string | null;
    check_out_at: string | null;
    checked_in_by: string | null;
    source: string;
    extras: Record<string, unknown>;
    waiting_list_position: number | null;
    reminder_sent_count: number;
    last_reminder_sent_at: string | null;
};

const STATUS_LABEL: Record<RegistrationStatus, string> = {
    PENDING: 'Verificación pendiente',
    CONFIRMED: 'Inscripción confirmada',
    CHECKED_IN: 'Check-in realizado',
    ABSENT: 'Ausente',
    CANCELLED: 'Cancelada',
    WAITLIST: 'Lista de espera',
};

function formatDate(iso: string | null): string {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return '';
        return d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    } catch {
        return '';
    }
}

function RegisterSuccess({ result, event, baseUrl }: { result: RegistrationResult; event: PublicEventInfo; baseUrl: string }) {
    const isPending = result.registration_status === 'PENDING';
    const isConfirmed = result.registration_status === 'CONFIRMED';
    const isCheckedIn = result.registration_status === 'CHECKED_IN';
    const isWaitlist = result.registration_status === 'WAITLIST';
    const showQr = isConfirmed || isCheckedIn;

    return (
        <div className="flex flex-col items-center justify-center text-center space-y-4 animate-in fade-in zoom-in duration-500">
            <div className="w-20 h-20 rounded-full flex items-center justify-center shadow-2xl"
                style={isPending
                    ? { background: 'hsl(var(--warning-muted))', color: 'hsl(var(--warning-text))' }
                    : isWaitlist
                        ? { background: 'hsl(var(--info-muted))', color: 'hsl(var(--info-text))' }
                        : { background: 'hsl(var(--success-muted))', color: 'hsl(var(--success-text))' }}>
                {isPending
                    ? <Mail size={40} strokeWidth={2.5} />
                    : isWaitlist
                        ? <Users size={40} strokeWidth={2.5} />
                        : <Check size={40} strokeWidth={3} />}
            </div>

            <div>
                <h1 className="text-lg sm:text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight">{STATUS_LABEL[result.registration_status]}</h1>
                {result.persona_name && (
                    <p className="text-sm font-medium text-[hsl(var(--text-secondary))] mt-1">¡Hola, {result.persona_name}!</p>
                )}
            </div>

            {isWaitlist && (
                <div className="p-4 rounded-lg text-sm font-semibold w-full text-left"
                    style={{ background: 'hsl(var(--info-muted))', color: 'hsl(var(--info-text))' }}>
                    El evento está lleno. Fuiste agregado a la lista de espera
                    {result.waiting_list_position != null ? ` en la posición ${result.waiting_list_position}` : ''}.
                    Te avisaremos si se libera un cupo.
                </div>
            )}

            {isPending && (
                <div className="p-4 rounded-lg text-sm font-semibold w-full text-left"
                    style={{ background: 'hsl(var(--warning-muted))', color: 'hsl(var(--warning-text))' }}>
                    Te enviamos un correo para confirmar tu inscripción. Revisa tu bandeja de entrada
                    (o spam) y haz clic en el enlace de verificación para activar tu QR.
                </div>
            )}

            {showQr && result.qr_token && (
                <>
                    <div className="p-4 bg-white rounded-md shadow-xl border border-[hsl(var(--border-primary))] flex items-center justify-center">
                        <QRCodeSVG
                            id="registration-qr-code"
                            value={`${baseUrl}/public/events/${event.id}/qr?token=${result.qr_token}`}
                            size={224}
                            level="H"
                            includeMargin
                        />
                    </div>
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        <QrCode size={14} /> Presenta este código en el ingreso
                    </div>
                </>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full text-left">
                <div className="rounded-lg border border-[hsl(var(--border))] p-3">
                    <div className="flex items-center gap-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        <Calendar size={13} /> Fecha
                    </div>
                    <div className="text-sm font-semibold text-[hsl(var(--text-primary))] mt-1">{formatDate(event.event_date)}</div>
                </div>
                {event.location && (
                    <div className="rounded-lg border border-[hsl(var(--border))] p-3">
                        <div className="flex items-center gap-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            <MapPin size={13} /> Lugar
                        </div>
                        <div className="text-sm font-semibold text-[hsl(var(--text-primary))] mt-1">{event.location}</div>
                    </div>
                )}
            </div>

            <a
                href={`${baseUrl}/public/events/${event.id}/qr?token=${result.qr_token ?? ''}`}
                target="_blank"
                rel="noreferrer"
                className="w-full py-2.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-white rounded-lg text-sm font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary)/30%)] transition-all flex items-center justify-center gap-2"
            >
                <QrCode size={16} /> Abrir mi código QR
            </a>
        </div>
    );
}

function RegisterForm({ event, baseUrl }: { event: PublicEventInfo; baseUrl: string }) {
    const [form, setForm] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        accept_contact: true,
    });
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [result, setResult] = useState<RegistrationResult | null>(null);
    const [errorDetail, setErrorDetail] = useState<string | null>(null);
    const [notRegistered, setNotRegistered] = useState(false);
    const [checkEmail, setCheckEmail] = useState('');
    const [checkPhone, setCheckPhone] = useState('');
    const [checking, setChecking] = useState(false);
    const [checkResult, setCheckResult] = useState<RegistrationResult | null>(null);
    const [checkError, setCheckError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('loading');
        setErrorDetail(null);
        try {
            const data = await apiFetch<RegistrationResult>(`/public/events/${event.id}/register`, {
                method: 'POST',
                body: {
                    first_name: form.first_name,
                    last_name: form.last_name,
                    email: form.email || null,
                    phone: form.phone || null,
                    accept_contact: form.accept_contact,
                    extras: {},
                },
                silent: true,
            });
            setResult(data);
            setStatus('success');
        } catch (err) {
            setStatus('error');
            if (err instanceof ApiError) {
                const detail = err.detail as { code?: string; detail?: string } | undefined;
                if (detail?.code === 'EVENT_FULL') {
                    setErrorDetail('El evento está lleno' + (event.waiting_list_enabled ? '. Fuiste agregado a la lista de espera.' : '.'));
                } else if (detail?.code === 'REGISTRATION_CLOSED') {
                    setErrorDetail('El periodo de registro para este evento ya cerró.');
                } else if (detail?.code === 'REGISTRATION_NOT_OPEN') {
                    setErrorDetail('El registro para este evento aún no está abierto.');
                } else {
                    setErrorDetail(detail?.detail || 'Ocurrió un error al registrarte. Inténtalo de nuevo.');
                }
            } else {
                setErrorDetail('Ocurrió un error al registrarte. Inténtalo de nuevo.');
            }
        }
    };

    const handleCheck = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!checkEmail && !checkPhone) return;
        setChecking(true);
        setCheckError(null);
        setCheckResult(null);
        try {
            const qs = new URLSearchParams();
            if (checkEmail) qs.set('email', checkEmail);
            if (checkPhone) qs.set('phone', checkPhone);
            const data = await apiFetch<RegistrationResult>(`/public/events/${event.id}/status?${qs.toString()}`, {
                silent: true,
            });
            setCheckResult(data);
            setNotRegistered(false);
        } catch (err) {
            setCheckResult(null);
            if (err instanceof ApiError && err.status === 404) {
                setNotRegistered(true);
                setCheckError(null);
            } else {
                setNotRegistered(false);
                setCheckError('No pudimos consultar tu inscripción. Inténtalo de nuevo.');
            }
        } finally {
            setChecking(false);
        }
    };

    const renderCheckStatus = () => {
        if (checkResult) {
            return (
                <div className="rounded-lg border border-[hsl(var(--border))] p-4 text-left">
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full"
                            style={{ background: checkResult.registration_status === 'CONFIRMED' || checkResult.registration_status === 'CHECKED_IN' ? 'hsl(var(--success))' : 'hsl(var(--warning))' }} />
                        <span className="text-sm font-bold text-[hsl(var(--text-primary))]">{STATUS_LABEL[checkResult.registration_status]}</span>
                    </div>
                    {checkResult.waiting_list_position != null && (
                        <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-1">
                            Posición en lista de espera: {checkResult.waiting_list_position}
                        </p>
                    )}
                    {checkResult.cancelled_at && (
                        <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-1">
                            Cancelada el {new Date(checkResult.cancelled_at).toLocaleString('es-CO')}
                        </p>
                    )}
                </div>
            );
        }
        if (notRegistered) {
            return (
                <div className="p-4 bg-warning-soft text-warning-text rounded-lg text-sm font-bold">
                    No encontramos una inscripción con esos datos.
                </div>
            );
        }
        return null;
    };

    if (status === 'success' && result) {
        return <RegisterSuccess result={result} event={event} baseUrl={baseUrl} />;
    }

    return (
        <div className="space-y-6">
            <form onSubmit={handleSubmit} className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-2">
                        <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-2">Nombres *</label>
                        <input
                            required
                            type="text"
                            value={form.first_name}
                            onChange={e => setForm({ ...form, first_name: e.target.value })}
                            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none font-bold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
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
                            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none font-bold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
                            placeholder="Tus apellidos"
                        />
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-2">
                        Correo Electrónico{event.requires_email_verification ? ' *' : ''}
                    </label>
                    <input
                        type="email"
                        value={form.email}
                        onChange={e => setForm({ ...form, email: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none font-bold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
                        placeholder="ejemplo@correo.com"
                    />
                    {event.requires_email_verification && (
                        <p className="text-xs font-medium text-[hsl(var(--text-secondary))] pl-2 flex items-center gap-1.5">
                            <ShieldCheck size={13} /> Recibirás un correo para confirmar tu inscripción.
                        </p>
                    )}
                </div>

                <div className="space-y-2">
                    <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-2">Teléfono móvil</label>
                    <input
                        type="tel"
                        value={form.phone}
                        onChange={e => setForm({ ...form, phone: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none font-bold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
                        placeholder="+57 300 000 0000"
                    />
                </div>

                <div className="pt-1">
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

                {status === 'error' && errorDetail && (
                    <div className="p-4 bg-danger-soft text-danger-text rounded-lg text-sm font-bold flex items-start gap-3">
                        <X size={18} className="shrink-0 mt-0.5" /> {errorDetail}
                    </div>
                )}

                <button
                    type="submit"
                    disabled={status === 'loading'}
                    className="w-full py-2.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-white rounded-lg text-sm font-semibold uppercase tracking-wide shadow-xl shadow-black/10 hover:shadow-[hsl(var(--info)/30%)] active:scale-[0.98] transition-all flex items-center justify-center gap-3 disabled:opacity-60 disabled:hover:bg-[hsl(var(--primary))]"
                >
                    {status === 'loading'
                        ? <><Loader2 size={18} className="animate-spin" /> Registrando...</>
                        : <>{event.capacity_max ? `Reservar cupo (${event.capacity_remaining ?? event.capacity_max} disponibles)` : 'Confirmar Registro'} <ArrowRight size={18} /></>}
                </button>
            </form>

            <div className="border-t border-[hsl(var(--border))] pt-5">
                <h2 className="text-sm font-bold text-[hsl(var(--text-primary))] mb-3 flex items-center gap-2">
                    <ShieldCheck size={15} /> ¿Ya te inscribiste?
                </h2>
                <form onSubmit={handleCheck} className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <input
                        type="email"
                        value={checkEmail}
                        onChange={e => setCheckEmail(e.target.value)}
                        placeholder="Correo con el que te registraste"
                        className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none text-sm font-semibold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
                    />
                    <input
                        type="tel"
                        value={checkPhone}
                        onChange={e => setCheckPhone(e.target.value)}
                        placeholder="O tu teléfono móvil"
                        className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:bg-[hsl(var(--bg-primary))] focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] outline-none text-sm font-semibold text-[hsl(var(--text-primary))] transition-all placeholder:text-[hsl(var(--text-secondary))] placeholder:font-medium"
                    />
                    <button
                        type="submit"
                        disabled={checking || (!checkEmail && !checkPhone)}
                        className="sm:col-span-2 py-2 bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] hover:text-white rounded-lg text-xs font-semibold uppercase tracking-wide transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        {checking ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                        Consultar mi inscripción
                    </button>
                </form>
                <div className="mt-3">{renderCheckStatus()}</div>
                {checkError && (
                    <div className="mt-3 p-4 bg-danger-soft text-danger-text rounded-lg text-sm font-bold">{checkError}</div>
                )}
            </div>
        </div>
    );
}

export default function PublicEventRegistrationPage() {
    const params = useParams();
    const eventId = (params?.event_id as string) ?? '';
    const [event, setEvent] = useState<PublicEventInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        if (!eventId) {
            setLoading(false);
            setError('Falta el código del evento.');
            return;
        }
        const load = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<PublicEventInfo>(`/public/events/${eventId}`, { silent: true });
                if (cancelled) return;
                if (!data.requires_registration) {
                    setEvent(data);
                    setError(null);
                    setLoading(false);
                    return;
                }
                setEvent(data);
                setError(null);
                setLoading(false);
            } catch (err) {
                if (cancelled) return;
                setEvent(null);
                setLoading(false);
                if (err instanceof ApiError && err.status === 404) {
                    setError('Este evento no existe o ya no está disponible.');
                } else {
                    setError('No pudimos cargar la información del evento.');
                }
            }
        };
        load();
        return () => { cancelled = true; };
    }, [eventId]);

    if (loading) {
        return (
            <div className="min-h-screen bg-[hsl(var(--surface-1))] flex items-center justify-center p-4">
                <div className="flex flex-col items-center gap-3 animate-pulse text-[hsl(var(--text-secondary))] font-bold">
                    <Loader2 size={28} className="animate-spin" />
                    Cargando evento...
                </div>
            </div>
        );
    }

    if (error && !event) {
        return (
            <div className="min-h-screen bg-[hsl(var(--surface-1))] flex items-center justify-center p-4">
                <div className="w-full max-w-md bg-[hsl(var(--bg-primary))] rounded-lg shadow-2xl border border-[hsl(var(--border))] p-6 text-center">
                    <div className="mx-auto w-16 h-16 rounded-full bg-danger-soft text-danger-text flex items-center justify-center mb-4">
                        <X size={32} />
                    </div>
                    <h1 className="text-lg font-bold text-[hsl(var(--text-primary))]">{error}</h1>
                    <p className="text-sm font-medium text-[hsl(var(--text-secondary))] mt-2">
                        Si crees que es un error, comunícate con el equipo del evento.
                    </p>
                </div>
            </div>
        );
    }

    if (!event) return null;

    const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';

    return (
        <div className="min-h-screen bg-[hsl(var(--surface-1))] flex items-center justify-center p-3 sm:p-4 relative overflow-hidden">
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[hsl(var(--info-muted))]/50 blur-[120px] rounded-full mix-blend-multiply pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[hsl(var(--info-muted))]/50 blur-[120px] rounded-full mix-blend-multiply pointer-events-none" />

            <div className="w-full max-w-xl bg-[hsl(var(--bg-primary))] rounded-lg shadow-2xl border border-[hsl(var(--border))] p-4 sm:p-6 relative z-10">
                <div className="flex flex-col items-center justify-center text-center space-y-3 mb-4">
                    <div className="w-16 h-8 bg-gradient-to-tr from-[hsl(var(--info))] to-[hsl(var(--info))] text-white rounded-lg flex items-center justify-center shadow-lg shadow-[hsl(var(--info)/30%)] rotate-3">
                        <Calendar size={28} className="drop-shadow-md" />
                    </div>
                    <div>
                        <p className="text-2xs font-bold uppercase tracking-widest text-[hsl(var(--primary))] mb-1">Pre-registro CCF</p>
                        <h1 className="text-lg sm:text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight">{event.name}</h1>
                        {event.description && (
                            <p className="text-sm font-medium text-[hsl(var(--text-secondary))] mt-2 max-w-md mx-auto">{event.description}</p>
                        )}
                    </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-5">
                    {event.event_date && (
                        <div className="rounded-lg border border-[hsl(var(--border))] p-3 flex items-center gap-3">
                            <Calendar size={16} className="text-[hsl(var(--primary))] shrink-0" />
                            <div>
                                <div className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fecha</div>
                                <div className="text-xs font-semibold text-[hsl(var(--text-primary))] capitalize">{formatDate(event.event_date)}</div>
                            </div>
                        </div>
                    )}
                    {event.location && (
                        <div className="rounded-lg border border-[hsl(var(--border))] p-3 flex items-center gap-3">
                            <MapPin size={16} className="text-[hsl(var(--primary))] shrink-0" />
                            <div>
                                <div className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Lugar</div>
                                <div className="text-xs font-semibold text-[hsl(var(--text-primary))]">{event.location}</div>
                            </div>
                        </div>
                    )}
                    {event.start_time && (
                        <div className="rounded-lg border border-[hsl(var(--border))] p-3 flex items-center gap-3">
                            <Clock size={16} className="text-[hsl(var(--primary))] shrink-0" />
                            <div>
                                <div className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Horario</div>
                                <div className="text-xs font-semibold text-[hsl(var(--text-primary))]">{event.start_time}{event.end_time ? ` - ${event.end_time}` : ''}</div>
                            </div>
                        </div>
                    )}
                    {event.capacity_max != null && (
                        <div className="rounded-lg border border-[hsl(var(--border))] p-3 flex items-center gap-3">
                            <Users size={16} className="text-[hsl(var(--primary))] shrink-0" />
                            <div>
                                <div className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Cupos</div>
                                <div className="text-xs font-semibold text-[hsl(var(--text-primary))]">
                                    {event.capacity_remaining != null && event.capacity_remaining > 0
                                        ? `${event.capacity_remaining} de ${event.capacity_max} disponibles`
                                        : 'Sin cupos disponibles'}
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {!event.is_open && (
                    <div className="p-4 bg-warning-soft text-warning-text rounded-lg text-sm font-bold mb-4 flex items-start gap-3">
                        <AlertTriangle size={18} className="shrink-0 mt-0.5" /> El registro para este evento no está disponible en este momento.
                    </div>
                )}

                {event.is_open && event.requires_registration ? (
                    <RegisterForm event={event} baseUrl={baseUrl} />
                ) : (
                    <div className="p-4 bg-warning-soft text-warning-text rounded-lg text-sm font-bold text-center">
                        Este evento no requiere pre-registro.
                    </div>
                )}
            </div>
        </div>
    );
}
