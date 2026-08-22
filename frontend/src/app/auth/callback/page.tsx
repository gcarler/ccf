"use client";

import { useEffect, useState, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

function AuthCallbackContent() {
    const router = useRouter();
    const { login } = useAuth();
    const [status, setStatus] = useState('Procesando autenticación...');

    useEffect(() => {
        async function handleAuth() {
            // 1. Extraer intención de curso y redirección de los parámetros URL antes de limpiar
            let targetRedirect: string | null = null;
            let targetCourseId: string | null = null;
            let targetCourseTitle: string | null = null;
            let alreadyEnrolled = false;

            if (typeof window !== 'undefined') {
                const searchParams = new URLSearchParams(window.location.search);
                targetRedirect = searchParams.get('redirect');
                targetCourseId = searchParams.get('course_id');
                targetCourseTitle = searchParams.get('course_title');
                alreadyEnrolled = searchParams.get('enrolled') === '1';

                // Si no vino por URL, revisar en localStorage
                if (!targetCourseId) {
                    try {
                        const stored = localStorage.getItem('ccf_pending_course');
                        if (stored) {
                            const parsed = JSON.parse(stored);
                            targetCourseId = parsed.id || parsed.course_id || null;
                            targetCourseTitle = parsed.title || parsed.course_title || null;
                            if (parsed.redirect && !targetRedirect) {
                                targetRedirect = parsed.redirect;
                            }
                        }
                    } catch {
                        // ignore parse errors
                    }
                }

                // Limpiar parámetros sensibles del historial
                window.history.replaceState({}, document.title, window.location.pathname);
            }

            let token: string | null = null;
            let refresh: string | null = null;

            setStatus('Validando sesión segura...');
            try {
                const refreshed = await apiFetch<{ access_token?: string; refresh_token?: string }>(
                    '/v3/auth/refresh',
                    { method: 'POST', silent: true },
                );
                token = refreshed.access_token || null;
                refresh = refreshed.refresh_token || null;
            } catch {
                token = null;
            }

            if (!token) {
                setStatus('Error: No se pudo validar la sesión');
                setTimeout(() => router.push('/login'), 3000);
                return;
            }

            setStatus('Autenticación exitosa. Preparando tu aula virtual...');
            await login(token, refresh ?? undefined);

            // 2. Extraer user ID del JWT y garantizar auto-matrícula
            let userId: string | null = null;
            try {
                const parts = token.split('.');
                if (parts.length === 3) {
                    const payload = JSON.parse(atob(parts[1]));
                    userId = payload.sub || null;
                }
            } catch {
                // ignore jwt decode errors
            }

            if (targetCourseId && userId) {
                try {
                    if (!alreadyEnrolled) {
                        setStatus('Matriculando en tu curso gratuito...');
                        await apiFetch('/academy/enrollments/', {
                            method: 'POST',
                            token,
                            body: { persona_id: userId, course_id: targetCourseId },
                        });
                    }
                    if (typeof window !== 'undefined') {
                        localStorage.removeItem('ccf_pending_course');
                    }
                    toast.success(
                        targetCourseTitle
                            ? `¡Bienvenido! Ya estás matriculado en "${targetCourseTitle}".`
                            : '¡Bienvenido a tu curso!'
                    );
                } catch (enrollErr) {
                    console.warn('Auto-enroll fallback warning:', enrollErr);
                }
            }

            // 3. Redirigir directamente al curso o al aula
            const destination = targetRedirect || (targetCourseId ? `/plataforma/academy/course/${targetCourseId}` : '/plataforma/academy');
            router.push(destination);
        }

        handleAuth();
    }, [login, router]); // login/router are stable

    return (
        <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--bg-muted))]">
            <div className="text-center">
                <Loader2 className="animate-spin mx-auto mb-4 text-ccf-blue-dark" size={32} />
                <p className="text-[hsl(var(--text-primary))] font-medium">{status}</p>
            </div>
        </div>
    );
}

export default function AuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center bg-[hsl(var(--bg-muted))]">
                <Loader2 className="animate-spin mx-auto mb-4 text-ccf-blue-dark" size={32} />
            </div>
        }>
            <AuthCallbackContent />
        </Suspense>
    );
}
