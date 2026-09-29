"use client";

import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  HeartPulse,
  Info,
  Loader2,
  RefreshCw,
  Search,
  ShieldAlert,
  User,
} from 'lucide-react';
import { DSButton, DSSkeleton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { StudentRiskProfile, WellnessSeverity, WellnessSignal } from '@/types/academy';

interface WellnessDrawerProps {
  open: boolean;
  onClose: () => void;
  offeringId: string;
  offeringTitle?: string | null;
  token: string | null;
  onSuccess?: () => void;
}

export default function WellnessDrawer({
  open,
  onClose,
  offeringId,
  offeringTitle,
  token,
  onSuccess,
}: WellnessDrawerProps) {
  const [signals, setSignals] = useState<WellnessSignal[]>([]);
  const [loading, setLoading] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [studentRiskProfile, setStudentRiskProfile] = useState<StudentRiskProfile | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  const fetchSignals = useCallback(async () => {
    if (!token || !offeringId) return;
    setLoading(true);
    try {
      const data = await apiFetch<WellnessSignal[]>(
        `/api/academy/wellness/${offeringId}/signals`,
        { token, cache: 'no-store' }
      );
      setSignals(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al sincronizar señales de bienestar'));
    } finally {
      setLoading(false);
    }
  }, [token, offeringId]);

  useEffect(() => {
    if (open && offeringId) {
      fetchSignals();
      setSelectedStudentId(null);
      setStudentRiskProfile(null);
    }
  }, [open, offeringId, fetchSignals]);

  const handleDetect = async () => {
    if (!token || !offeringId) return;
    setDetecting(true);
    try {
      const res = await apiFetch<{ detected_count: number; summary: string }>(
        '/api/academy/wellness/detect',
        {
          token,
          method: 'POST',
          body: JSON.stringify({ offering_id: offeringId }),
        }
      );
      toast.success(res.summary);
      await fetchSignals();
      if (onSuccess) onSuccess();
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error en el escaneo predictivo de bienestar'));
    } finally {
      setDetecting(false);
    }
  };

  const handleResolve = async (signalId: string) => {
    if (!token) return;
    setResolvingId(signalId);
    try {
      await apiFetch<WellnessSignal>(
        `/api/academy/wellness/signals/${signalId}/resolve`,
        {
          token,
          method: 'POST',
        }
      );
      toast.success('Señal marcada como resuelta satisfactoriamente');
      setSignals((prev) =>
        prev.map((s) => (s.id === signalId ? { ...s, is_resolved: true } : s))
      );
      if (onSuccess) onSuccess();
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al resolver la señal'));
    } finally {
      setResolvingId(null);
    }
  };

  const handleInspectProfile = async (studentId: string) => {
    if (!token) return;
    setSelectedStudentId(studentId);
    setLoadingProfile(true);
    try {
      const profile = await apiFetch<StudentRiskProfile>(
        `/api/academy/wellness/student/${studentId}/risk-profile`,
        { token, cache: 'no-store' }
      );
      setStudentRiskProfile(profile);
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al consultar perfil de riesgo'));
    } finally {
      setLoadingProfile(false);
    }
  };

  const filteredSignals = signals.filter((s) => {
    if (filterSeverity === 'all') return true;
    if (filterSeverity === 'active') return !s.is_resolved;
    return s.severity === filterSeverity;
  });

  const getSeverityBadgeClass = (sev: WellnessSeverity) => {
    switch (sev) {
      case 'critical':
        return 'bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))] border border-[hsl(var(--destructive)/0.3)]';
      case 'high':
        return 'bg-[hsl(var(--warning,38_92%_50%)/0.15)] text-[hsl(var(--warning,38_92%_50%))] border border-[hsl(var(--warning,38_92%_50%)/0.3)]';
      case 'medium':
        return 'bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.3)]';
      default:
        return 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]';
    }
  };

  const getSignalTypeLabel = (st: string) => {
    switch (st) {
      case 'grade_risk':
        return 'Riesgo de Nota';
      case 'engagement_drop':
        return 'Baja Actividad';
      case 'stress_indicator':
        return 'Sobrecarga / Estrés';
      case 'absence_pattern':
        return 'Inasistencia Crítica';
      default:
        return st;
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <HeartPulse className="size-5 text-[hsl(var(--destructive))]" />
          <span>Monitor de Bienestar Estudiantil</span>
        </div>
      }
      subtitle={offeringTitle || 'Comisión Académica'}
      width="w-full sm:max-w-3xl"
    >
      <div className="space-y-6 text-xs text-[hsl(var(--foreground))]">
        {/* Banner de Acción Rápida */}
        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h4 className="font-bold text-sm text-[hsl(var(--foreground))] flex items-center gap-1.5">
                <ShieldAlert className="size-4 text-[hsl(var(--primary))]" />
                Escaneo y Diagnóstico Pedagógico
              </h4>
              <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5">
                Detecta de forma proactiva estudiantes con notas inferiores al 60%, defensas reprobadas, inasistencias críticas o inactividad socrática superior a 7 días.
              </p>
            </div>
            <DSButton
              onClick={handleDetect}
              disabled={detecting}
              className="h-8 px-3 text-xs inline-flex items-center gap-1.5 shrink-0"
            >
              {detecting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Analizando...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="size-3.5" />
                  <span>Detectar Automático</span>
                </>
              )}
            </DSButton>
          </div>

          {/* Métricas rápidas */}
          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[hsl(var(--border))] text-center">
            <div className="p-2 rounded-lg bg-[hsl(var(--surface-2))]">
              <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Señales Totales</span>
              <span className="font-bold text-sm text-[hsl(var(--foreground))]">{signals.length}</span>
            </div>
            <div className="p-2 rounded-lg bg-[hsl(var(--surface-2))]">
              <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Activas (Pendientes)</span>
              <span className="font-bold text-sm text-[hsl(var(--destructive))]">
                {signals.filter((s) => !s.is_resolved).length}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-[hsl(var(--surface-2))]">
              <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Críticas</span>
              <span className="font-bold text-sm text-[hsl(var(--primary))]">
                {signals.filter((s) => s.severity === 'critical' && !s.is_resolved).length}
              </span>
            </div>
          </div>
        </div>

        {/* Perfil de Riesgo Detallado (si está seleccionado un estudiante) */}
        {selectedStudentId && (
          <div className="p-4 rounded-xl border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.04)] space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-xs uppercase tracking-wider text-[hsl(var(--primary))] flex items-center gap-1.5">
                <User className="size-3.5" />
                Perfil de Riesgo del Estudiante
              </span>
              <button
                type="button"
                onClick={() => setSelectedStudentId(null)}
                className="text-xs text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--foreground))]"
              >
                Cerrar Perfil
              </button>
            </div>

            {loadingProfile ? (
              <div className="space-y-2">
                <DSSkeleton className="h-6 w-1/3 rounded" />
                <DSSkeleton className="h-14 w-full rounded" />
              </div>
            ) : studentRiskProfile ? (
              <div className="space-y-2.5">
                <div className="flex items-center gap-3">
                  <div className="text-center px-3 py-1.5 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Score de Riesgo</span>
                    <span className="font-bold text-base text-[hsl(var(--destructive))]">
                      {studentRiskProfile.risk_score} / 100
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))]">
                      Nivel: {studentRiskProfile.risk_level}
                    </span>
                    <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1">
                      {studentRiskProfile.active_signals_count} señales activas registradas en la plataforma.
                    </p>
                  </div>
                </div>

                <div className="space-y-1 pt-2 border-t border-[hsl(var(--border))]">
                  <span className="text-[11px] font-bold text-[hsl(var(--foreground))]">
                    Recomendaciones Pedagógicas Sugeridas:
                  </span>
                  <ul className="list-disc pl-4 space-y-0.5 text-[11px] text-[hsl(var(--text-secondary))]">
                    {studentRiskProfile.recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* Filtros de Lista */}
        <div className="flex items-center justify-between gap-2">
          <span className="font-bold text-xs uppercase tracking-wider text-[hsl(var(--text-secondary))]">
            Señales Registradas ({filteredSignals.length})
          </span>
          <div className="flex items-center gap-1.5">
            {['all', 'active', 'critical', 'high'].map((sev) => (
              <button
                key={sev}
                type="button"
                onClick={() => setFilterSeverity(sev)}
                className={`px-2 py-1 rounded text-[10px] font-bold uppercase transition-colors ${
                  filterSeverity === sev
                    ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                    : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3,var(--surface-2)))]'
                }`}
              >
                {sev === 'all' ? 'Todas' : sev === 'active' ? 'Pendientes' : sev}
              </button>
            ))}
          </div>
        </div>

        {/* Tabla / Lista de Señales */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <DSSkeleton key={i} className="h-16 w-full rounded-xl" />
            ))}
          </div>
        ) : filteredSignals.length === 0 ? (
          <div className="p-8 text-center rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
            <CheckCircle2 className="size-8 mx-auto text-[hsl(var(--primary))] opacity-60" />
            <p className="font-bold text-xs mt-2 text-[hsl(var(--foreground))]">
              No hay señales que coincidan con el filtro
            </p>
            <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5">
              Los estudiantes de esta comisión mantienen un estado de bienestar pedagógico óptimo.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {filteredSignals.map((sig) => {
              const detailsReason = (sig.details?.reason as string) || '';
              return (
                <div
                  key={sig.id}
                  className={`p-3.5 rounded-xl border transition-all ${
                    sig.is_resolved
                      ? 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] opacity-60'
                      : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${getSeverityBadgeClass(sig.severity)}`}>
                          {sig.severity}
                        </span>
                        <span className="font-bold text-xs text-[hsl(var(--foreground))]">
                          {getSignalTypeLabel(sig.signal_type)}
                        </span>
                        {sig.is_resolved ? (
                          <span className="text-[10px] font-medium text-[hsl(var(--primary))] flex items-center gap-1">
                            <CheckCircle2 className="size-3" /> Resuelta
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium text-[hsl(var(--destructive))] flex items-center gap-1">
                            <Clock className="size-3" /> Pendiente
                          </span>
                        )}
                      </div>

                      {detailsReason && (
                        <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                          {detailsReason}
                        </p>
                      )}

                      <div className="flex items-center gap-3 pt-1 text-[10px] text-[hsl(var(--text-secondary))]">
                        <span>Detectada: {new Date(sig.detected_at).toLocaleDateString()}</span>
                        {sig.student_name && (
                          <span className="font-medium text-[hsl(var(--foreground))]">
                            Estudiante: {sig.student_name}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col gap-1.5 shrink-0 items-end">
                      {!sig.is_resolved && (
                        <button
                          type="button"
                          onClick={() => handleResolve(sig.id)}
                          disabled={resolvingId === sig.id}
                          className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 flex items-center gap-1"
                        >
                          {resolvingId === sig.id && <Loader2 className="size-3 animate-spin" />}
                          Resolver
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleInspectProfile(sig.student_id)}
                        className="text-[10px] font-medium text-[hsl(var(--primary))] hover:underline flex items-center gap-1"
                      >
                        <Search className="size-3" />
                        Ver Perfil
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </RightPanel>
  );
}
