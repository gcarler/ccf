"use client";

import React, { useState, useEffect } from 'react';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { AcademicPeriod } from '@/types/academy';
import { Calendar, Save, Loader2 } from 'lucide-react';

interface AcademicPeriodDrawerProps {
  open: boolean;
  onClose: () => void;
  period: AcademicPeriod | null;
  token: string | null;
  onSuccess: (saved: AcademicPeriod) => void;
}

export default function AcademicPeriodDrawer({
  open,
  onClose,
  period,
  token,
  onSuccess,
}: AcademicPeriodDrawerProps) {
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    period_type: 'semestral',
    start_date: '',
    end_date: '',
    enrollment_start_date: '',
    enrollment_end_date: '',
    grading_deadline: '',
    status: 'open',
    is_active: true,
  });

  useEffect(() => {
    if (period) {
      setFormData({
        code: period.code || '',
        name: period.name || '',
        period_type: period.period_type || 'semestral',
        start_date: period.start_date || '',
        end_date: period.end_date || '',
        enrollment_start_date: period.enrollment_start_date || '',
        enrollment_end_date: period.enrollment_end_date || '',
        grading_deadline: period.grading_deadline || '',
        status: period.status || 'open',
        is_active: period.is_active ?? true,
      });
    } else {
      const year = new Date().getFullYear();
      setFormData({
        code: `${year}-I`,
        name: `Semestre Académico ${year}-I`,
        period_type: 'semestral',
        start_date: `${year}-02-01`,
        end_date: `${year}-06-30`,
        enrollment_start_date: `${year}-01-10`,
        enrollment_end_date: `${year}-01-31`,
        grading_deadline: `${year}-07-05`,
        status: 'open',
        is_active: true,
      });
    }
  }, [period, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (!formData.name.trim() || !formData.code.trim()) {
      toast.error('Nombre y código del período son obligatorios');
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        code: formData.code.trim().toUpperCase(),
        name: formData.name.trim(),
        period_type: formData.period_type,
        start_date: formData.start_date,
        end_date: formData.end_date,
        enrollment_start_date: formData.enrollment_start_date || null,
        enrollment_end_date: formData.enrollment_end_date || null,
        grading_deadline: formData.grading_deadline || null,
        status: formData.status,
        is_active: formData.is_active,
      };

      if (period?.id) {
        const updated = await apiFetch<AcademicPeriod>(`/academy/admin/periods/${period.id}`, {
          method: 'PATCH',
          token,
          body: payload,
        });
        toast.success('Período académico actualizado');
        onSuccess(updated);
      } else {
        const created = await apiFetch<AcademicPeriod>('/academy/admin/periods', {
          method: 'POST',
          token,
          body: payload,
        });
        toast.success('Período académico aperturado exitosamente');
        onSuccess(created);
      }
      onClose();
    } catch (err: unknown) {
      const errorObj = err as { detail?: string; message?: string };
      toast.error(errorObj?.detail || errorObj?.message || 'Error al guardar el período');
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
          <Calendar className="size-5 text-[hsl(var(--primary))]" />
          <span>{period ? 'Editar Período Académico' : 'Aperturar Período Académico'}</span>
        </div>
      }
      subtitle="Configura el ciclo lectivo, fechas de matrícula y plazo de corte de notas."
      width="w-full sm:max-w-xl"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-4 text-[hsl(var(--foreground))]">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Código</label>
            <input
              type="text"
              required
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              placeholder="EJ: 2026-I"
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Nombre del Período</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ej: Semestre Académico 2026-I"
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Modalidad de Período</label>
            <select
              value={formData.period_type}
              onChange={(e) => setFormData({ ...formData, period_type: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            >
              <option value="semestral">Semestral (Regular)</option>
              <option value="cuatrimestral">Cuatrimestral</option>
              <option value="modular">Modular / Mensual</option>
              <option value="intensivo">Intensivo / Vacacional</option>
              <option value="anual">Anual</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Estado del Período</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            >
              <option value="open">Abierto (Matrículas / Clases)</option>
              <option value="in_progress">En Curso</option>
              <option value="grading">En Calificaciones (Cortes activos)</option>
              <option value="closed">Cerrado / Consolidado</option>
              <option value="draft">Borrador</option>
            </select>
          </div>
        </div>

        {/* Fechas de Clases */}
        <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
            Fechas Lectivas Oficiales
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Inicio de Clases</label>
              <input
                type="date"
                required
                value={formData.start_date}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Cierre de Clases</label>
              <input
                type="date"
                required
                value={formData.end_date}
                onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
              />
            </div>
          </div>
        </div>

        {/* Plazos de Calificación y Matrículas */}
        <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
            Plazos de Matrícula y Calificación Docente
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Inicio Matrícula</label>
              <input
                type="date"
                value={formData.enrollment_start_date}
                onChange={(e) => setFormData({ ...formData, enrollment_start_date: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Límite Matrícula</label>
              <input
                type="date"
                value={formData.enrollment_end_date}
                onChange={(e) => setFormData({ ...formData, enrollment_end_date: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">
              Fecha Límite Cierre de Notas Docentes
            </label>
            <input
              type="date"
              value={formData.grading_deadline}
              onChange={(e) => setFormData({ ...formData, grading_deadline: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
        </div>

        {/* Acciones */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[hsl(var(--border))] mt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-bold rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-5 py-2 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center gap-1.5 hover:opacity-90 transition-opacity disabled:opacity-50 shadow-md"
          >
            {submitting ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
            <span>{period ? 'Guardar Período' : 'Aperturar Período'}</span>
          </button>
        </div>
      </form>
    </RightPanel>
  );
}
