"use client";

import React, { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
    Calendar as CalendarIcon,
    RefreshCw,
    Clock4,
    CheckCircle2,
    ShieldCheck,
    Link2,
    ExternalLink
} from 'lucide-react';
import CommunityToolbarChip from '@/components/community/ToolbarChip';

type ConnectedAccount = {
    id: string;
    email: string;
    calendarCount: number;
    lastSync: string;
    active: boolean;
};

type UpcomingEvent = {
    id: string;
    title: string;
    date: string;
    time: string;
    location: string;
    synced: boolean;
};

const defaultAccounts: ConnectedAccount[] = [
    { id: '1', email: 'carlos@ccf.mx', calendarCount: 5, lastSync: 'Hace 2 h', active: true },
    { id: '2', email: 'comunidad@ccf.mx', calendarCount: 3, lastSync: 'Ayer 21:00', active: true },
    { id: '3', email: 'eventos@ccf.mx', calendarCount: 2, lastSync: 'Nunca', active: false }
];

const upcomingEvents: UpcomingEvent[] = [
    { id: 'evt-1', title: 'Reunión Creativos', date: 'Vie, 21 Mar', time: '18:30', location: 'Campus Norte', synced: true },
    { id: 'evt-2', title: 'Encuentro de Grupos Vida', date: 'Sáb, 22 Mar', time: '10:00', location: 'Hub Online', synced: true },
    { id: 'evt-3', title: 'Lanzamiento campaña Generosidad', date: 'Lun, 24 Mar', time: '12:00', location: 'Sala War Room', synced: false }
];

export default function CalendarIntegrationPage() {
    const router = useRouter();
    const [accounts, setAccounts] = useState(defaultAccounts);
    const [isSyncing, setIsSyncing] = useState(false);
    const [lastFullSync, setLastFullSync] = useState('Hace 6 minutos');
    const activeAccounts = accounts.filter((account) => account.active);
    const scopes = ['calendar.readonly', 'calendar.events', 'userinfo.email'];

    const coverage = useMemo(() => {
        const totalCalendars = accounts.reduce((acc, account) => acc + account.calendarCount, 0);
        return {
            connectedCalendars: totalCalendars,
            activeAccounts: activeAccounts.length
        };
    }, [accounts, activeAccounts.length]);

    const handleSync = () => {
        if (isSyncing) return;
        setIsSyncing(true);
        setTimeout(() => {
            setIsSyncing(false);
            setLastFullSync('Hace unos segundos');
            setAccounts((prev) => prev.map((account) => ({ ...account, lastSync: 'Hace 0 min' })));
        }, 2000);
    };

    const handleConnectGoogle = () => {
        router.push('https://accounts.google.com/o/oauth2/v2/auth');
    };

    const toggleAccount = (accountId: string) => {
        setAccounts((prev) =>
            prev.map((account) =>
                account.id === accountId ? { ...account, active: !account.active } : account
            )
        );
    };

    return (
        <div className="space-y-10 animate-in fade-in duration-500 px-4 sm:px-6 pb-16 max-w-5xl mx-auto">
            <header className="rounded-[3rem] border border-[hsl(var(--border))] bg-gradient-to-br from-white to-slate-50 dark:from-slate-900 dark:to-slate-950 p-8 space-y-6">
                <div className="flex items-center gap-3 text-[10px] font-medium uppercase tracking-[0.35em] text-[hsl(var(--text-secondary))]">
                    <span>Integraciones</span>
                    <span className="opacity-40">/</span>
                    <span className="text-[hsl(var(--primary))]">Google Calendar</span>
                </div>
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
                    <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.4em] text-[hsl(var(--primary))]">Sincronización 2 vías</p>
                        <h1 className="text-[28px] md:text-[32px] font-semibold text-[hsl(var(--text-primary))] tracking-tight leading-tight">Mantén tus eventos ClickUp y Google Calendar en perfecta sincronía.</h1>
                        <p className="text-[13px] md:text-sm text-[hsl(var(--text-secondary))] font-medium mt-2 max-w-2xl">
                            Conecta múltiples cuentas de Google Workspace, define qué calendarios se sincronizan y déjale a ClickUp la consolidación de recordatorios, permisos y disponibilidad.
                        </p>
                    </div>
                    <div className="flex flex-col gap-3">
                        <button
                            type="button"
                            onClick={handleConnectGoogle}
                            className="px-5 h-12 rounded-2xl border border-[hsl(var(--border))] bg-white text-[10px] font-semibold uppercase tracking-[0.35em] flex items-center gap-3 shadow-sm"
                        >
                            <span className="size-7 rounded-full bg-[#4285F4] text-white font-bold text-xs flex items-center justify-center">G</span>
                            Conectar con Google
                        </button>
                        <button
                            type="button"
                            onClick={handleSync}
                            disabled={isSyncing}
                            className="px-5 h-12 rounded-2xl bg-[hsl(var(--text-primary))] text-white text-[10px] font-semibold uppercase tracking-[0.4em] flex items-center gap-3 disabled:opacity-50"
                        >
                            <RefreshCw size={16} className={isSyncing ? 'animate-spin' : ''} />
                            {isSyncing ? 'Sincronizando…' : 'Sincronizar ahora'}
                        </button>
                    </div>
                </div>
            </header>

            <section className="rounded-[2.5rem] border border-[hsl(var(--border))] bg-white dark:bg-slate-900/80 p-6 space-y-6">
                <div className="flex flex-wrap items-center gap-4">
                    <div className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                        <CalendarIcon size={20} className="text-[hsl(var(--primary))]" />
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[hsl(var(--text-secondary))]">Calendarios conectados</p>
                            <p className="text-xl font-semibold text-[hsl(var(--text-primary))]">{coverage.connectedCalendars}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 px-4 py-3 rounded-2xl border border-[hsl(var(--border))]">
                        <CheckCircle2 size={20} className="text-emerald-500" />
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[hsl(var(--text-secondary))]">Cuentas activas</p>
                            <p className="text-xl font-semibold text-[hsl(var(--text-primary))]">{coverage.activeAccounts}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 px-4 py-3 rounded-2xl border border-[hsl(var(--border))]">
                        <Clock4 size={20} className="text-amber-500" />
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[hsl(var(--text-secondary))]">Última sincronización</p>
                            <p className="text-xl font-semibold text-[hsl(var(--text-primary))]">{lastFullSync}</p>
                        </div>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {scopes.map((scope) => (
                        <CommunityToolbarChip key={scope} label={scope} size="sm" />
                    ))}
                    <CommunityToolbarChip label="Ver documentación" icon={ExternalLink} size="sm" onClick={() => router.push('https://developers.google.com/calendar')} />
                </div>
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                <div className="lg:col-span-3 space-y-4 rounded-[2.5rem] border border-[hsl(var(--border))] bg-white dark:bg-slate-900/70 p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.35em] text-[hsl(var(--text-secondary))]">Cuentas conectadas</p>
                            <h2 className="text-xl font-semibold text-[hsl(var(--text-primary))]">Google Workspace</h2>
                        </div>
                        <button className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[hsl(var(--primary))]" onClick={handleConnectGoogle}>
                            + Añadir cuenta
                        </button>
                    </div>
                    <div className="space-y-4">
                        {accounts.map((account) => (
                            <div
                                key={account.id}
                                className={`rounded-2xl border px-5 py-4 flex items-center justify-between ${account.active ? 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]' : 'border-dashed border-[hsl(var(--border))] bg-transparent'}`}
                            >
                                <div>
                                    <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{account.email}</p>
                                    <p className="text-[12px] text-[hsl(var(--text-secondary))]">{account.calendarCount} calendarios · Último sync {account.lastSync || '—'}</p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => toggleAccount(account.id)}
                                    className={`px-4 h-10 rounded-2xl text-[10px] font-semibold uppercase tracking-[0.3em] ${account.active ? 'bg-[hsl(var(--text-primary))] text-white' : 'border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))]'}`}
                                >
                                    {account.active ? 'Activo' : 'Activar'}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="lg:col-span-2 space-y-4 rounded-[2.5rem] border border-[hsl(var(--border))] bg-white dark:bg-slate-900/70 p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.35em] text-[hsl(var(--text-secondary))]">Próximos eventos</p>
                            <h2 className="text-xl font-semibold text-[hsl(var(--text-primary))]">Agenda sincronizada</h2>
                        </div>
                        <CommunityToolbarChip label="Semana" active variant="solid" size="sm" />
                    </div>
                    <div className="space-y-3">
                        {upcomingEvents.map((event) => (
                            <div key={event.id} className="rounded-2xl border border-[hsl(var(--border))] p-4 flex items-start gap-3">
                                <div className="rounded-xl bg-[hsl(var(--surface-2))] px-3 py-2 text-[11px] font-semibold text-[hsl(var(--text-primary))]">
                                    {event.date}
                                </div>
                                <div className="flex-1 space-y-1">
                                    <p className="text-[15px] font-semibold text-[hsl(var(--text-primary))]">{event.title}</p>
                                    <p className="text-[12px] text-[hsl(var(--text-secondary))]">{event.time} · {event.location}</p>
                                    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.3em] ${event.synced ? 'text-emerald-500' : 'text-amber-500'}`}>
                                        <CheckCircle2 size={12} /> {event.synced ? 'Google actualizado' : 'Pendiente de enviar'}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <section className="rounded-[3rem] border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-3))] p-8 space-y-4 text-center">
                <ShieldCheck size={36} className="mx-auto text-[hsl(var(--primary))]" />
                <h3 className="text-2xl font-semibold text-[hsl(var(--text-primary))]">Autorizaciones OAuth confiables</h3>
                <p className="text-[13px] text-[hsl(var(--text-secondary))] max-w-2xl mx-auto">
                    ClickUp solo solicitará permisos de lectura/escritura para los calendarios seleccionados. Puedes revocar la autorización desde Google Security en cualquier momento.
                </p>
                <div className="flex flex-wrap justify-center gap-3 mt-4">
                    <CommunityToolbarChip label="Ver auditoría" icon={Link2} size="sm" />
                    <CommunityToolbarChip label="Política de privacidad" icon={ExternalLink} size="sm" onClick={() => router.push('/privacy')} />
                </div>
            </section>
        </div>
    );
}
