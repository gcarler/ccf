"use client";

import React, { useState, useEffect } from 'react';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { StudyPlanSubject, GradingScheme } from '@/types/academy';
import { BookOpen, Save, Loader2, Sparkles } from 'lucide-react';

interface StudyPlanSubjectDrawerProps {
  open: boolean;
  onClose: () => void;
  studyPlanId: string;
  subject: StudyPlanSubject | null;
  schemes: GradingScheme[];
  token: string | null;
  onSuccess: (saved: StudyPlanSubject) => void;
}

export default function StudyPlanSubjectDrawer({
  open,
  onClose,
  studyPlanId,
  subject,
  schemes,
  token,
  onSuccess,
}: StudyPlanSubjectDrawerProps) {
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    level_number: 1,
    credits: 3,
    weekly_hours_theory: 2,
    weekly_hours_practice: 2,
    weekly_hours_independent: 4,
    is_mandatory: true,
    default_grading_scheme_id: '',
    prerequisite_codes: '',
  });

  useEffect(() => {
    if (subject) {
      setFormData({
        code: subject.code || '',
        name: subject.name || '',
        level_number: subject.level_number || 1,
        credits: subject.credits ?? 3,
        weekly_hours_theory: subject.weekly_hours_theory ?? 2,
        weekly_hours_practice: subject.weekly_hours_practice ?? 2,
        weekly_hours_independent: subject.weekly_hours_independent ?? 4,
        is_mandatory: subject.is_mandatory ?? true,
        default_grading_scheme_id: subject.default_grading_scheme_id || '',
        prerequisite_codes: (subject.prerequisite_codes || []).join(', '),
      });
    } else {
      const defaultScheme = schemes.find((s) => s.is_default);
      setFormData({
        code: '',
        name: '',
        level_number: 1,
        credits: 3,
        weekly_hours_theory: 2,
        weekly_hours_practice: 2,
        weekly_hours_independent: 4,
        is_mandatory: true,
        default_grading_scheme_id: defaultScheme ? defaultScheme.id : (schemes[0]?.id || ''),
        prerequisite_codes: '',
      });
    }
  }, [subject, open, schemes]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (!formData.name.trim() || !formData.code.trim()) {
      toast.error('Nombre y código de la asignatura son obligatorios');
      return;
    }

    try {
      setSubmitting(true);
      const prereqs = formData.prerequisite_codes
        .split(',')
        .map((p) => p.trim().toUpperCase())
        .filter(Boolean);

      const payload = {
        code: formData.code.trim().toUpperCase(),
        name: formData.name.trim(),
        level_number: formData.level_number,
        credits: formData.credits,
        weekly_hours_theory: formData.weekly_hours_theory,
        weekly_hours_practice: formData.weekly_hours_practice,
        weekly_hours_independent: formData.weekly_hours_independent,
        is_mandatory: formData.is_mandatory,
        default_grading_scheme_id: formData.default_grading_scheme_id || null,
        prerequisite_codes: prereqs.length > 0 ? prereqs : null,
      };

      if (subject?.id) {
        const updated = await apiFetch<StudyPlanSubject>(`/academy/admin/subjects/${subject.id}`, {
          method: 'PATCH',
          token,
          body: payload,
        });
        toast.success('Asignatura actualizada en la malla curricular');
        onSuccess(updated);
      } else {
        const created = await apiFetch<StudyPlanSubject>(`/academy/admin/study-plans/${studyPlanId}/subjects`, {
          method: 'POST',
          token,
          body: payload,
        });
        toast.success('Asignatura incorporada al pensum con éxito');
        onSuccess(created);
      }
      onClose();
    } catch (err: unknown) {
      const errorObj = err as { detail?: string; message?: string };
      toast.error(errorObj?.detail || errorObj?.message || 'Error al guardar la materia');
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
          <BookOpen className="size-5 text-[hsl(var(--primary))]" />
          <span>{subject ? 'Editar Materia del Pensum' : 'Añadir Materia al Pensum'}</span>
        </div>
      }
      subtitle="Configura el nivel semestral, créditos educativos y horas de trabajo de la asignatura."
      width="w-full sm:max-w-xl"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-4 text-[hsl(var(--foreground))]">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Código Materia</label>
            <input
              type="text"
              required
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              placeholder="EJ: TEO-101"
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Nombre de la Asignatura</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ej: Teología Sistemática I"
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
        </div>

        {/* Nivel y Créditos Educativos */}
        <div className="p-3.5 rounded-lg border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.04)] space-y-3">
          <div className="flex items-center gap-1.5 text-xs font-bold text-[hsl(var(--primary))] uppercase tracking-wider">
            <Sparkles className="size-4" />
            <span>Créditos Educativos & Nivel Curricular</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">
                Semestre / Nivel
              </label>
              <input
                type="number"
                min={1}
                max={20}
                required
                value={formData.level_number}
                onChange={(e) => setFormData({ ...formData, level_number: parseInt(e.target.value) || 1 })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-[hsl(var(--primary))] mb-1 block">
                Créditos Educativos
              </label>
              <input
                type="number"
                min={1}
                max={20}
                required
                value={formData.credits}
                onChange={(e) => setFormData({ ...formData, credits: parseInt(e.target.value) || 1 })}
                className="w-full px-3 py-2 text-sm font-bold text-[hsl(var(--primary))] rounded-lg border border-[hsl(var(--primary))] bg-[hsl(var(--surface-2))]"
              />
            </div>
          </div>
          <p className="text-[11px] text-[hsl(var(--text-secondary))] leading-relaxed">
            * <strong>Valor ponderado:</strong> Las materias con mayor cantidad de créditos pesan proporcionalmente más en el Promedio Ponderado Acumulado (PAPA/GPA) del estudiante.
          </p>
        </div>

        {/* Intensidad Horaria Semanal */}
        <div className="grid grid-cols-3 gap-2.5 p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
          <div>
            <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Horas Teoría / sem</label>
            <input
              type="number"
              min={0}
              value={formData.weekly_hours_theory}
              onChange={(e) => setFormData({ ...formData, weekly_hours_theory: parseInt(e.target.value) || 0 })}
              className="w-full px-2 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Horas Práctica / sem</label>
            <input
              type="number"
              min={0}
              value={formData.weekly_hours_practice}
              onChange={(e) => setFormData({ ...formData, weekly_hours_practice: parseInt(e.target.value) || 0 })}
              className="w-full px-2 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Trabajo Indep. / sem</label>
            <input
              type="number"
              min={0}
              value={formData.weekly_hours_independent}
              onChange={(e) => setFormData({ ...formData, weekly_hours_independent: parseInt(e.target.value) || 0 })}
              className="w-full px-2 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
        </div>

        {/* Esquema de Calificación Predeterminado */}
        <div>
          <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">
            Esquema de Cortes por Defecto
          </label>
          <select
            value={formData.default_grading_scheme_id}
            onChange={(e) => setFormData({ ...formData, default_grading_scheme_id: e.target.value })}
            className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
          >
            <option value="">Seleccionar esquema de cortes...</option>
            {schemes.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.cuts.length} cortes) {s.is_default ? '★ Predeterminado' : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Prerrequisitos */}
        <div>
          <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">
            Códigos de Prerrequisitos (separados por coma)
          </label>
          <input
            type="text"
            value={formData.prerequisite_codes}
            onChange={(e) => setFormData({ ...formData, prerequisite_codes: e.target.value })}
            placeholder="Ej: TEO-101, HERM-100"
            className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
          />
        </div>

        {/* Obligatoria */}
        <label className="flex items-center gap-2 cursor-pointer p-2 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
          <input
            type="checkbox"
            checked={formData.is_mandatory}
            onChange={(e) => setFormData({ ...formData, is_mandatory: e.target.checked })}
            className="size-4 rounded text-[hsl(var(--primary))]"
          />
          <span className="text-xs font-bold">Materia de carácter obligatorio para graduación</span>
        </label>

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
            <span>{subject ? 'Guardar Materia' : 'Incorporar Materia'}</span>
          </button>
        </div>
      </form>
    </RightPanel>
  );
}
