"use client";

import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { DSSkeleton } from '@/design';
import {
  HeartPulse,
  GraduationCap,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Bell,
  Sparkles,
  BookOpen,
  LifeBuoy,
} from 'lucide-react';
import type { StudentRiskProfile, WellnessAlert } from '@/types/academy';
import clsx from 'clsx';

export default function StudentWellnessPage() {
  const { user, token, isAuthenticated } = useAuth();
  const [profile, setProfile] = useState<StudentRiskProfile | null>(null);
  const [alerts, setAlerts] = useState<WellnessAlert[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchWellnessData = useCallback(async () => {
    if (!token || !user?.id) return;
    setLoading(true);
    try {
      const [profileData, alertsData] = await Promise.all([
        apiFetch<StudentRiskProfile>(
          `/api/academy/wellness/student/${user.id}/risk-profile`,
          { token, cache: 'no-store' }
        ).catch(() => null),
        apiFetch<WellnessAlert[]>(
          '/api/academy/wellness/my-alerts',
          { token, cache: 'no-store' }
        ).catch(() => []),
      ]);

      if (profileData) setProfile(profileData);
      setAlerts(Array.isArray(alertsData) ? alertsData : []);
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al sincronizar datos de bienestar'));
    } finally {
      setLoading(false);
    }
  }, [token, user?.id]);

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchWellnessData();
    }
  }, [isAuthenticated, token, fetchWellnessData]);

  if (loading) {
    return (
      <div className="p-6 space-y-4 bg-[hsl(var(--bg-primary))] min-h-screen">
        <DSSkeleton className="h-32 rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <DSSkeleton className="h-48 rounded-xl" />
          <DSSkeleton className="h-48 rounded-xl" />
        </div>
      </div>
    );
  }

  const riskScore = profile?.risk_score ?? 0;
  const riskLevel = profile?.risk_level ?? 'low';

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] text-[hsl(var(--foreground))]">
      <WorkspaceToolbar
        breadcrumbs={[
          { label: 'Academia', icon: GraduationCap },
          { label: 'Bienestar Estudiantil', icon: HeartPulse },
        ]}
      />

      {/* Header */}
      <div className="px-6 py-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
        <div className="flex items-center gap-2">
          <span className="text-2xs font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)]">
            Acompañamiento Integral
          </span>
          <span className="text-2xs font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
            Campus OS Cognitivo
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight mt-1 text-[hsl(var(--foreground))]">
          Monitor de Bienestar Estudiantil
        </h1>
        <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
          Seguimiento continuo de tu ritmo de aprendizaje, alertas formativas preventivas y recomendaciones de salud académica.
        </p>
      </div>

      {/* Body */}
      <div className="p-6 flex-1 overflow-y-auto space-y-6 max-w-5xl">
        {/* Tarjeta Principal de Diagnóstico */}
        <div className="p-6 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center md:text-left">
            <span className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
              Estado de Salud Académica & Rendimiento
            </span>
            <div className="flex items-center gap-3 justify-center md:justify-start flex-wrap">
              <span className="text-3xl font-extrabold text-[hsl(var(--foreground))]">
                {riskScore} <span className="text-base text-[hsl(var(--text-secondary))] font-normal">/ 100</span>
              </span>
              <span
                className={clsx(
                  'px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide',
                  riskLevel === 'critical' && 'bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))] border border-[hsl(var(--destructive)/0.3)]',
                  riskLevel === 'high' && 'bg-[hsl(var(--warning,38_92%_50%)/0.15)] text-[hsl(var(--warning,38_92%_50%))] border border-[hsl(var(--warning,38_92%_50%)/0.3)]',
                  riskLevel === 'medium' && 'bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.3)]',
                  riskLevel === 'low' && 'bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] border border-[hsl(var(--border))]'
                )}
              >
                Riesgo: {riskLevel}
              </span>
            </div>
            <p className="text-xs text-[hsl(var(--text-secondary))] max-w-xl">
              {riskScore === 0
                ? '¡Excelente! No tienes señales de riesgo registradas. Tu ritmo de estudio y participación se encuentran en balance óptimo.'
                : 'Se han detectado factores de atención preventiva para optimizar tu experiencia y evitar sobrecargas pedagógicas.'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-center shrink-0 w-full md:w-56">
            <HeartPulse className="size-8 mx-auto text-[hsl(var(--primary))] mb-1" />
            <span className="text-xs font-bold text-[hsl(var(--foreground))] block">Acompañamiento Activo</span>
            <span className="text-[11px] text-[hsl(var(--text-secondary))]">
              Tutoría Socrática 24/7 disponible en plataforma
            </span>
          </div>
        </div>

        {/* Recomendaciones Formativas */}
        {profile && profile.recommendations.length > 0 && (
          <div className="p-5 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
            <h3 className="font-bold text-sm text-[hsl(var(--foreground))] flex items-center gap-2">
              <Sparkles className="size-4 text-[hsl(var(--primary))]" />
              Recomendaciones Personalizadas para tu Bienestar
            </h3>
            <ul className="space-y-2">
              {profile.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2.5 text-xs text-[hsl(var(--text-secondary))] p-2.5 rounded-lg bg-[hsl(var(--surface-2))]">
                  <CheckCircle2 className="size-4 text-[hsl(var(--primary))] shrink-0 mt-0.5" />
                  <span className="text-[hsl(var(--foreground))] font-medium">{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Alertas Preventivas y Notificaciones */}
        <div className="p-5 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
          <h3 className="font-bold text-sm text-[hsl(var(--foreground))] flex items-center gap-2">
            <Bell className="size-4 text-[hsl(var(--primary))]" />
            Notificaciones y Alertas Preventivas ({alerts.length})
          </h3>

          {alerts.length === 0 ? (
            <div className="p-6 text-center rounded-xl bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-secondary))]">
              No tienes alertas preventivas pendientes en este momento.
            </div>
          ) : (
            <div className="space-y-2">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="p-3.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex items-start justify-between gap-3 text-xs"
                >
                  <div className="space-y-1">
                    <span className="font-bold text-[hsl(var(--foreground))] block">
                      {alert.message}
                    </span>
                    <span className="text-[10px] text-[hsl(var(--text-secondary))]">
                      Enviada: {new Date(alert.sent_at).toLocaleDateString()}
                    </span>
                  </div>
                  {alert.read_at ? (
                    <span className="text-[10px] font-medium text-[hsl(var(--primary))]">Leída</span>
                  ) : (
                    <span className="text-[10px] font-bold text-[hsl(var(--destructive))]">Nueva</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
