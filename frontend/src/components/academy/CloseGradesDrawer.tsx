"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { PeriodOffering, OfferingGradesDetail } from '@/types/academy';
import { Lock, AlertTriangle, CheckCircle2, Loader2, BookOpen, UserX } from 'lucide-react';

interface CloseGradesDrawerProps {
  open: boolean;
  onClose: () => void;
  offering: PeriodOffering | null;
  token: string | null;
  onClosedSuccess?: () => void;
}

export default function CloseGradesDrawer({
  open,
  onClose,
  offering,
  token,
  onClosedSuccess,
}: CloseGradesDrawerProps) {
  const [gradesDetail, setGradesDetail] = useState<OfferingGradesDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [closing, setClosing] = useState(false);

  const fetchGrades = useCallback(async () => {
    if (!offering || !token) return;
    setLoading(true);
    try {
      const data = await apiFetch<OfferingGradesDetail>(
        `/api/academy/admin/offerings/${offering.id}/grades`,
        { token }
      );
      setGradesDetail(data);
    } catch {
      toast.error('Error al cargar la sábana de notas para validación');
    } finally {
      setLoading(false);
    }
  }, [offering, token]);

  useEffect(() => {
    if (open && offering) {
      fetchGrades();
    }
  }, [open, offering, fetchGrades]);

  // Check completeness: each record must have non-null grade for every cut
  const cuts = gradesDetail?.cuts || [];
  const records = gradesDetail?.records || [];

  const incompleteStudents = records.filter((rec) => {
    const grades = rec.grades_by_cut || {};
    return cuts.some((cut) => {
      const cutId = cut.id;
      return !cutId || grades[cutId] === null || grades[cutId] === undefined;
    });
  });

  const canClose = records.length > 0 && incompleteStudents.length === 0;

  const handleCloseActa = async () => {
    if (!offering || !token) return;
    setClosing(true);
    try {
      await apiFetch(`/api/academy/admin/offerings/${offering.id}/close-grades`, {
        method: 'POST',
        token,
      });
      toast.success('Acta cerrada y calificaciones consolidadas exitosamente');
      onClosedSuccess?.();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al cerrar el acta académica';
      toast.error(msg);
    } finally {
      setClosing(false);
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title="Cierre Oficial de Acta"
      subtitle={offering ? `${offering.subject_name || 'Comisión'} - ${offering.group_name}` : ''}
      width={540}
    >
      <div className="space-y-6 p-6">
        {offering && (
          <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4 text-xs space-y-1">
            <div className="flex items-center gap-2 font-semibold text-[hsl(var(--foreground))]">
              <BookOpen className="h-4 w-4 text-[hsl(var(--primary))]" />
              <span>{offering.subject_name} ({offering.subject_code})</span>
            </div>
            <div className="text-[hsl(var(--muted-foreground))] flex gap-4 pt-1">
              <span>Período: <strong>{offering.period_code || 'Activo'}</strong></span>
              <span>Cortes evaluativos: <strong>{cuts.length}</strong></span>
              <span>Estudiantes: <strong>{records.length}</strong></span>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12 text-[hsl(var(--muted-foreground))]">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : (
          <>
            {/* Status overview */}
            {canClose ? (
              <div className="rounded-xl border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.08)] p-4 flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-[hsl(var(--primary))] shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <h4 className="font-semibold text-[hsl(var(--foreground))]">
                    Acta lista para cierre oficial
                  </h4>
                  <p className="text-[hsl(var(--muted-foreground))]">
                    Todos los {records.length} estudiantes cuentan con sus calificaciones completas en los {cuts.length} cortes. Al cerrar, se bloqueará cualquier edición futura.
                  </p>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.08)] p-4 flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-[hsl(var(--destructive))] shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <h4 className="font-semibold text-[hsl(var(--destructive))]">
                    No es posible cerrar el acta aún
                  </h4>
                  <p className="text-[hsl(var(--muted-foreground))]">
                    {records.length === 0
                      ? 'No hay estudiantes matriculados con registro de notas en esta comisión.'
                      : `Existen ${incompleteStudents.length} estudiante(s) con calificaciones incompletas en uno o más cortes.`}
                  </p>
                </div>
              </div>
            )}

            {/* Incomplete roster list if any */}
            {incompleteStudents.length > 0 && (
              <div className="space-y-2">
                <h5 className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--destructive))] flex items-center gap-1.5">
                  <UserX className="h-3.5 w-3.5" />
                  Estudiantes con cortes faltantes:
                </h5>
                <div className="divide-y divide-[hsl(var(--border))] rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] overflow-hidden">
                  {incompleteStudents.map((rec) => (
                    <div key={rec.id} className="p-2.5 text-xs flex justify-between items-center">
                      <span className="font-medium text-[hsl(var(--foreground))]">
                        {rec.student_name}
                      </span>
                      <span className="text-[10px] text-[hsl(var(--destructive))] font-mono">
                        Cortes pendientes
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action button */}
            <div className="pt-4 border-t border-[hsl(var(--border))]">
              <button
                type="button"
                disabled={!canClose || closing}
                onClick={handleCloseActa}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-semibold transition-opacity disabled:opacity-40 hover:opacity-90 shadow-sm"
              >
                {closing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
                Cerrar Acta Oficial y Bloquear Calificaciones
              </button>
            </div>
          </>
        )}
      </div>
    </RightPanel>
  );
}
