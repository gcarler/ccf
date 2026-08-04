'use client';

import React, { useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { QrCode, Check, X, Loader2, Calendar, ShieldCheck } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { apiFetch, ApiError } from '@/lib/http';

type RegistrationStatus =
    | 'PENDING'
    | 'CONFIRMED'
    | 'CHECKED_IN'
    | 'ABSENT'
    | 'CANCELLED'
    | 'WAITLIST';

type RegistrationResult = {
    id: string;
    registration_status: RegistrationStatus;
    qr_token: string | null;
    waiting_list_position: number | null;
    cancelled_at: string | null;
    confirmed_at: string | null;
    check_in_at: string | null;
};

function QrTicket({ token, eventId, cancelToken }: { token: string; eventId: string; cancelToken: string }) {
    const [error, setError] = useState<string | null>(null);
    const [cancelling, setCancelling] = useState(false);
    const [cancelled, setCancelled] = useState(false);
    const [confirmCancel, setConfirmCancel] = useState(false);

    const handleCancel = async () => {
        if (!cancelToken) return;
        setCancelling(true);
        setError(null);
        try {
            await apiFetch<RegistrationResult>(`/public/events/${eventId}/cancel`, {
                method: 'POST',
                body: { cancel_token: cancelToken },
                silent: true,
            });
            setCancelled(true);
        } catch (err) {
            if (err instanceof ApiError) {
                const detail = err.detail as { code?: string; detail?: string } | undefined;
                setError(detail?.detail || 'No pudimos cancelar tu inscripción.');
            } else {
                setError('No pudimos cancelar tu inscripción.');
            }
        } finally {
            setCancelling(false);
        }
    };

    if (cancelled) {
        return (
            <div className="flex flex-col items-center justify-center text-center space-y-4 animate-in fade-in zoom-in duration-500">
                <div className="w-20 h-20 rounded-full flex items-center justify-center shadow-2xl"
                    style={{ background: 'hsl(var(--success-muted))', color: 'hsl(var(--success-text))' }}>
                    <Check size={40} strokeWidth={3} />
                </div>
                <h1 className="text-lg font-bold text-[hsl(var(--text-primary))]">Inscripción cancelada</h1>
                <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">
                    Tu cupo fue liberado. Si el evento tiene lista de espera, se notificará al siguiente inscrito.
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center text-center space-y-4 animate-in fade-in zoom-in duration-500">
            <div className="p-4 bg-white rounded-md shadow-xl border border-[hsl(var(--border-primary))] flex items-center justify-center">
                <QRCodeSVG
                    id="event-ticket-qr"
                    value={typeof window !== 'undefined' ? `${window.location.origin}/public/events/${eventId}/qr?token=${token}` : ''}
                    size={256}
                    level="H"
                    includeMargin
                />
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                <QrCode size={14} /> Presenta este código en el ingreso
            </div>

            {error && (
                <div className="p-4 bg-danger-soft text-danger-text rounded-lg text-sm font-bold w-full">{error}</div>
            )}

            {cancelToken && (
                <div className="pt-2 w-full border-t border-[hsl(var(--border))]">
                    {!confirmCancel ? (
                        <button
                            onClick={() => setConfirmCancel(true)}
                            className="w-full py-2.5 rounded-lg text-sm font-semibold uppercase tracking-wide border border-[hsl(var(--danger))] text-[hsl(var(--danger))] hover:bg-danger-soft transition-all"
                        >
                            Cancelar mi inscripción
                        </button>
                    ) : (
                        <div className="space-y-2">
                            <p className="text-xs font-semibold text-[hsl(var(--text-secondary))]">
                                ¿Seguro que deseas cancelar tu inscripción? Esta acción libera tu cupo.
                            </p>
                            <div className="grid grid-cols-2 gap-2">
                                <button
                                    onClick={() => setConfirmCancel(false)}
                                    disabled={cancelling}
                                    className="py-2.5 rounded-lg text-sm font-semibold uppercase tracking-wide border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] transition-all disabled:opacity-50"
                                >
                                    No, conservar
                                </button>
                                <button
                                    onClick={handleCancel}
                                    disabled={cancelling}
                                    className="py-2.5 rounded-lg text-sm font-semibold uppercase tracking-wide bg-danger-soft text-danger-text hover:bg-[hsl(var(--danger))] hover:text-white transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    {cancelling ? <Loader2 size={14} className="animate-spin" /> : <X size={14} />} Sí, cancelar
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default function PublicEventQrPage() {
    const params = useParams();
    const searchParams = useSearchParams();
    const eventId = (params?.event_id as string) ?? '';
    const token = searchParams?.get('token') ?? '';
    const cancelToken = searchParams?.get('cancel') ?? '';

    if (!token) {
        return (
            <div className="min-h-screen bg-[hsl(var(--surface-1))] flex items-center justify-center p-4">
                <div className="w-full max-w-md bg-[hsl(var(--bg-primary))] rounded-lg shadow-2xl border border-[hsl(var(--border))] p-6 text-center">
                    <div className="mx-auto w-16 h-16 rounded-full bg-danger-soft text-danger-text flex items-center justify-center mb-4">
                        <X size={32} />
                    </div>
                    <h1 className="text-lg font-bold text-[hsl(var(--text-primary))]">Código inválido</h1>
                    <p className="text-sm font-medium text-[hsl(var(--text-secondary))] mt-2">
                        Este enlace no contiene un código QR válido.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[hsl(var(--surface-1))] flex items-center justify-center p-3 sm:p-4 relative overflow-hidden">
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[hsl(var(--info-muted))]/50 blur-[120px] rounded-full mix-blend-multiply pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[hsl(var(--info-muted))]/50 blur-[120px] rounded-full mix-blend-multiply pointer-events-none" />

            <div className="w-full max-w-lg bg-[hsl(var(--bg-primary))] rounded-lg shadow-2xl border border-[hsl(var(--border))] p-4 sm:p-6 relative z-10">
                <div className="flex flex-col items-center justify-center text-center space-y-2 mb-4">
                    <div className="w-16 h-8 bg-gradient-to-tr from-[hsl(var(--info))] to-[hsl(var(--info))] text-white rounded-lg flex items-center justify-center shadow-lg shadow-[hsl(var(--info)/30%)] rotate-3">
                        <Calendar size={28} className="drop-shadow-md" />
                    </div>
                    <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] tracking-tight">Código de Ingreso</h1>
                    <p className="text-sm font-medium text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <ShieldCheck size={14} /> CCF Eventos
                    </p>
                </div>

                <QrTicket token={token} eventId={eventId} cancelToken={cancelToken} />
            </div>
        </div>
    );
}
