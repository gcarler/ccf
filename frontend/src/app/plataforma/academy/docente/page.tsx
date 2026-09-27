"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { PeriodOffering } from '@/types/academy';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import EmptyState from '@/components/ui/EmptyState';
import { DSSkeleton } from '@/design';
import OfferingGradesDrawer from '@/components/academy/OfferingGradesDrawer';
import { GraduationCap, Award, BookOpen, Users, Clock, Sparkles } from 'lucide-react';
import clsx from 'clsx';

export default function DocentePortalPage() {
  const { token, isAuthenticated } = useAuth();
  const [offerings, setOfferings] = useState<PeriodOffering[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedOfferingId, setSelectedOfferingId] = useState<string>('');
  const [gradesDrawerOpen, setGradesDrawerOpen] = useState(false);

  const fetchMyOfferings = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await apiFetch<PeriodOffering[]>('/api/academy/docente/my-offerings', {
        token,
        cache: 'no-store',
      });
      setOfferings(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Error al sincronizar tus comisiones asignadas');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchMyOfferings();
    }
  }, [isAuthenticated, token, fetchMyOfferings]);

  if (loading) {
    return (
      <div className="p-6 space-y-4 bg-[hsl(var(--bg-primary))] min-h-screen">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <DSSkeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] text-[hsl(var(--foreground))]">
      <WorkspaceToolbar
        breadcrumbs={[
          { label: 'Academia', icon: GraduationCap },
          { label: 'Portal Docente', icon: Award },
        ]}
      />

      {/* Header */}
      <div className="px-6 py-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
        <div className="flex items-center gap-2">
          <span className="text-2xs font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)]">
            Cuerpo Docente Canónico
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight mt-1 text-[hsl(var(--foreground))]">
          Mis Comisiones & Registro de Calificaciones
        </h1>
        <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
          Consulta las asignaturas a tu cargo, gestiona las notas de tus estudiantes por corte y supervisa el progreso académico.
        </p>
      </div>

      {/* Body */}
      <div className="p-6 flex-1 overflow-y-auto">
        {offerings.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No tienes comisiones docentes asignadas actualmente"
            description="Cuando la dirección académica te asigne a un grupo formativo para el período activo, aparecerá aquí."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {offerings.map((off) => (
              <div
                key={off.id}
                className="p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col justify-between hover:border-[hsl(var(--primary)/0.4)] transition-all"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] font-mono">
                      {off.subject_code} • {off.credits} Créditos
                    </span>
                    <span className={clsx(
                      'px-2 py-0.5 rounded-full text-[10px] font-bold uppercase',
                      off.status === 'closed'
                        ? 'bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))]'
                        : 'bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]'
                    )}>
                      {off.status}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-[hsl(var(--foreground))] mt-2.5">
                    {off.subject_name}
                  </h3>
                  <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5 font-medium">
                    Grupo: <strong className="text-[hsl(var(--foreground))]">{off.group_name}</strong> • Período: {off.period_code}
                  </p>

                  <div className="mt-4 pt-3 border-t border-[hsl(var(--border))] space-y-1.5 text-xs text-[hsl(var(--text-secondary))]">
                    <div className="flex justify-between items-center">
                      <span className="flex items-center gap-1.5">
                        <Award className="size-3.5 text-[hsl(var(--primary))]" />
                        Esquema:
                      </span>
                      <span className="font-semibold text-[hsl(var(--foreground))]">
                        {off.grading_scheme_name || 'Estándar'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="flex items-center gap-1.5">
                        <Users className="size-3.5 text-[hsl(var(--primary))]" />
                        Estudiantes inscritos:
                      </span>
                      <span className="font-bold text-[hsl(var(--primary))]">
                        {off.enrolled_count} matriculados
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-[hsl(var(--border))]">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedOfferingId(off.id);
                      setGradesDrawerOpen(true);
                    }}
                    className="w-full py-2.5 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center justify-center gap-2 shadow-sm transition-all hover:opacity-90"
                  >
                    <Award className="size-4" />
                    <span>Calificar Cortes de la Comisión</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Drawer Lateral de Calificaciones (0 modals) */}
      <OfferingGradesDrawer
        open={gradesDrawerOpen}
        onClose={() => setGradesDrawerOpen(false)}
        offeringId={selectedOfferingId}
        token={token}
        onSuccess={() => fetchMyOfferings()}
      />
    </div>
  );
}
