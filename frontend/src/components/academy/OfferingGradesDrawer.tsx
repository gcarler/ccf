"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { OfferingGradesDetail, StudentSubjectRecord } from '@/types/academy';
import { Award, Save, Loader2, UserCheck, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';

interface OfferingGradesDrawerProps {
  open: boolean;
  onClose: () => void;
  offeringId: string;
  token: string | null;
  onSuccess?: () => void;
}

export default function OfferingGradesDrawer({
  open,
  onClose,
  offeringId,
  token,
  onSuccess,
}: OfferingGradesDrawerProps) {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [detail, setDetail] = useState<OfferingGradesDetail | null>(null);
  const [localGrades, setLocalGrades] = useState<Record<string, Record<string, number | null>>>({});

  const loadGrades = useCallback(async () => {
    if (!token || !offeringId) return;
    try {
      setLoading(true);
      const data = await apiFetch<OfferingGradesDetail>(`/academy/admin/offerings/${offeringId}/grades`, {
        token,
        cache: 'no-store',
      });
      setDetail(data);

      // Prepopulate local state: persona_id -> { cut_id: grade_value }
      const initial: Record<string, Record<string, number | null>> = {};
      data.records.forEach((rec) => {
        initial[rec.persona_id] = { ...(rec.grades_by_cut || {}) };
      });
      setLocalGrades(initial);
    } catch (err: unknown) {
      console.error(err);
      toast.error('No pudimos cargar la sábana de notas de la comisión');
    } finally {
      setLoading(false);
    }
  }, [token, offeringId]);

  useEffect(() => {
    if (open && offeringId) {
      loadGrades();
    }
  }, [open, offeringId, loadGrades]);

  const handleGradeChange = (personaId: string, cutId: string, value: string) => {
    const num = value === '' ? null : parseFloat(value);
    setLocalGrades((prev) => ({
      ...prev,
      [personaId]: {
        ...(prev[personaId] || {}),
        [cutId]: num,
      },
    }));
  };

  const calculatePreviewFinalGrade = (personaId: string): number | null => {
    if (!detail?.cuts) return null;
    const studentGrades = localGrades[personaId];
    if (!studentGrades) return null;

    let total = 0;
    let anyGraded = false;
    for (const cut of detail.cuts) {
      const g = cut.id ? studentGrades[cut.id] : null;
      if (g !== null && g !== undefined && !isNaN(g)) {
        total += g * (cut.weight_percent / 100);
        anyGraded = true;
      }
    }
    return anyGraded ? Math.round(total * 100) / 100 : null;
  };

  const handleSaveAll = async () => {
    if (!token || !detail) return;
    try {
      setSubmitting(true);
      const gradesToSubmit: { persona_id: string; cut_id: string; grade_value: number | null }[] = [];

      Object.entries(localGrades).forEach(([personaId, cutsMap]) => {
        Object.entries(cutsMap).forEach(([cutId, gradeVal]) => {
          gradesToSubmit.push({
            persona_id: personaId,
            cut_id: cutId,
            grade_value: gradeVal,
          });
        });
      });

      await apiFetch(`/academy/admin/offerings/${offeringId}/grades`, {
        method: 'POST',
        token,
        body: {
          offering_id: offeringId,
          grades: gradesToSubmit,
        },
      });

      toast.success('Calificaciones guardadas y actas recalculadas con éxito');
      await loadGrades();
      onSuccess?.();
    } catch (err: unknown) {
      const errorObj = err as { detail?: string; message?: string };
      toast.error(errorObj?.detail || errorObj?.message || 'Error al persistir calificaciones');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2 text-[hsl(var(--foreground))]">
          <Award className="size-5 text-[hsl(var(--primary))]" />
          <span>Sábana de Calificaciones & Actas</span>
        </div>
      }
      subtitle={
        detail
          ? `${detail.subject_name} (${detail.subject_code}) — ${detail.credits} Créditos — Período ${detail.period_code}`
          : 'Registro de notas por cortes y cálculo ponderado en vivo'
      }
      width="w-full sm:max-w-4xl"
    >
      <div className="flex flex-col h-full text-[hsl(var(--foreground))]">
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 gap-3 text-[hsl(var(--text-secondary))]">
            <Loader2 className="size-8 animate-spin text-[hsl(var(--primary))]" />
            <p className="text-sm">Cargando sábana de calificaciones...</p>
          </div>
        ) : !detail || detail.records.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-[hsl(var(--text-secondary))] gap-2">
            <UserCheck className="size-12 text-[hsl(var(--text-secondary))]" />
            <p className="text-sm font-bold text-[hsl(var(--foreground))]">No hay estudiantes inscritos en esta comisión</p>
            <p className="text-xs">Los estudiantes matriculados aparecerán aquí para calificar sus cortes.</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col p-4 gap-4 overflow-y-auto">
            {/* Cabecera Informativa de Cortes */}
            <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                  Esquema de Cortes:
                </span>
                <div className="flex items-center gap-2">
                  {detail.cuts.map((cut) => (
                    <span
                      key={cut.id || cut.name}
                      className="px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] font-semibold"
                    >
                      {cut.name} ({cut.weight_percent}%)
                    </span>
                  ))}
                </div>
              </div>
              <span className="text-[11px] font-bold text-[hsl(var(--primary))]">
                {detail.credits} Créditos Educativos
              </span>
            </div>

            {/* Tabla de Calificaciones */}
            <div className="rounded-lg border border-[hsl(var(--border))] overflow-hidden bg-[hsl(var(--surface-1))]">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wider text-[11px]">
                    <th className="p-3">Estudiante</th>
                    {detail.cuts.map((cut) => (
                      <th key={cut.id || cut.name} className="p-3 text-center">
                        <div>{cut.name}</div>
                        <div className="text-[10px] font-normal text-[hsl(var(--text-secondary))]">{cut.weight_percent}%</div>
                      </th>
                    ))}
                    <th className="p-3 text-center">Nota Final</th>
                    <th className="p-3 text-center">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border))]">
                  {detail.records.map((rec) => {
                    const previewFinal = calculatePreviewFinalGrade(rec.persona_id);
                    const isApproved = previewFinal !== null && previewFinal >= 70.0;
                    return (
                      <tr key={rec.id} className="hover:bg-[hsl(var(--surface-2)/0.5)] transition-colors">
                        <td className="p-3 font-semibold text-[hsl(var(--foreground))]">
                          {rec.student_name}
                        </td>
                        {detail.cuts.map((cut) => {
                          const cutVal = cut.id ? localGrades[rec.persona_id]?.[cut.id] : null;
                          return (
                            <td key={cut.id || cut.name} className="p-2 text-center">
                              <input
                                type="number"
                                step="0.1"
                                min={0}
                                max={100}
                                value={cutVal !== null && cutVal !== undefined ? cutVal : ''}
                                onChange={(e) => cut.id && handleGradeChange(rec.persona_id, cut.id, e.target.value)}
                                placeholder="—"
                                className="w-16 px-2 py-1 text-center font-bold rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                              />
                            </td>
                          );
                        })}
                        <td className="p-3 text-center font-bold text-sm">
                          {previewFinal !== null ? (
                            <span
                              className={clsx(
                                isApproved ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--destructive))]'
                              )}
                            >
                              {previewFinal.toFixed(1)}
                            </span>
                          ) : (
                            <span className="text-[hsl(var(--text-secondary))]">—</span>
                          )}
                        </td>
                        <td className="p-3 text-center">
                          {previewFinal !== null ? (
                            <span
                              className={clsx(
                                'px-2 py-0.5 rounded text-[10px] font-bold uppercase',
                                isApproved
                                  ? 'bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))]'
                                  : 'bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))]'
                              )}
                            >
                              {isApproved ? 'Aprobado' : 'Reprobado'}
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] font-bold">
                              En Curso
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Barra de Acciones */}
            <div className="flex items-center justify-between pt-3 border-t border-[hsl(var(--border))] mt-auto">
              <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                * Los cambios se aplican al acta consolidada y actualizan el promedio ponderado de los estudiantes.
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-bold rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                >
                  Cerrar
                </button>
                <button
                  type="button"
                  onClick={handleSaveAll}
                  disabled={submitting}
                  className="px-5 py-2 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center gap-1.5 hover:opacity-90 transition-opacity disabled:opacity-50 shadow-md"
                >
                  {submitting ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
                  <span>Guardar Notas y Recalcular</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </RightPanel>
  );
}
