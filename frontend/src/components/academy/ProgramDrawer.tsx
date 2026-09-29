"use client";

import React, { useState, useEffect } from 'react';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { AcademicProgram, ProgramType } from '@/types/academy';
import { GraduationCap, Loader2, Save, X } from 'lucide-react';
import clsx from 'clsx';

interface ProgramDrawerProps {
  open: boolean;
  onClose: () => void;
  program: AcademicProgram | null;
  token: string | null;
  onSuccess: (saved: AcademicProgram) => void;
}

const PROGRAM_TYPES: { value: ProgramType; label: string; desc: string }[] = [
  { value: 'curso_libre', label: 'Curso Libre', desc: 'Formación abierta, corta y puntual' },
  { value: 'diplomado', label: 'Diplomado', desc: 'Especialización práctica de mediana duración' },
  { value: 'carrera', label: 'Carrera / Licenciatura', desc: 'Formación formal estructurada en pensum' },
  { value: 'especializacion', label: 'Especialización', desc: 'Profundización profesional de posgrado' },
  { value: 'maestria', label: 'Maestría', desc: 'Estudios avanzados de maestría' },
  { value: 'doctorado', label: 'Doctorado', desc: 'Investigación académica doctoral' },
  { value: 'taller', label: 'Taller / Seminario', desc: 'Sesiones intensivas prácticas' },
  { value: 'certificacion', label: 'Certificación', desc: 'Validación de competencias ministeriales' },
  { value: 'otro', label: 'Personalizado', desc: 'Cualquier otro proceso formativo dinámico' },
];

export default function ProgramDrawer({
  open,
  onClose,
  program,
  token,
  onSuccess,
}: ProgramDrawerProps) {
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    program_type: 'diplomado' as ProgramType,
    level_name: '',
    total_duration_type: 'semestres',
    total_duration_units: 2,
    total_credits: 0,
    modality: 'presencial',
    has_teachers: true,
    teachers_can_grade: true,
    min_passing_grade: 70.0,
    grading_scale_max: 100.0,
    min_attendance_percent: 80.0,
    is_active: true,
  });

  useEffect(() => {
    if (program) {
      setFormData({
        code: program.code || '',
        name: program.name || '',
        description: program.description || '',
        program_type: (program.program_type as ProgramType) || 'diplomado',
        level_name: program.level_name || '',
        total_duration_type: program.total_duration_type || 'semestres',
        total_duration_units: program.total_duration_units || 2,
        total_credits: program.total_credits || 0,
        modality: program.modality || 'presencial',
        has_teachers: program.has_teachers ?? true,
        teachers_can_grade: program.teachers_can_grade ?? true,
        min_passing_grade: program.min_passing_grade ?? 70.0,
        grading_scale_max: program.grading_scale_max ?? 100.0,
        min_attendance_percent: program.min_attendance_percent ?? 80.0,
        is_active: program.is_active ?? true,
      });
    } else {
      setFormData({
        code: '',
        name: '',
        description: '',
        program_type: 'diplomado',
        level_name: '',
        total_duration_type: 'semestres',
        total_duration_units: 2,
        total_credits: 0,
        modality: 'presencial',
        has_teachers: true,
        teachers_can_grade: true,
        min_passing_grade: 70.0,
        grading_scale_max: 100.0,
        min_attendance_percent: 80.0,
        is_active: true,
      });
    }
  }, [program, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (!formData.name.trim() || !formData.code.trim()) {
      toast.error('Nombre y código del programa son obligatorios');
      return;
    }

    try {
      setSubmitting(true);
      if (program?.id) {
        const updated = await apiFetch<AcademicProgram>(`/academy/admin/programs/${program.id}`, {
          method: 'PATCH',
          token,
          body: formData,
        });
        toast.success('Programa actualizado correctamente');
        onSuccess(updated);
      } else {
        const created = await apiFetch<AcademicProgram>('/academy/admin/programs', {
          method: 'POST',
          token,
          body: formData,
        });
        toast.success('Programa académico creado exitosamente');
        onSuccess(created);
      }
      onClose();
    } catch (err: unknown) {
      const errorObj = err as { detail?: string; message?: string };
      toast.error(errorObj?.detail || errorObj?.message || 'Error al guardar el programa');
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
          <GraduationCap className="size-5 text-[hsl(var(--primary))]" />
          <span>{program ? 'Editar Proceso Formativo' : 'Nuevo Proceso Formativo'}</span>
        </div>
      }
      subtitle="Configura cualquier tipo de formación académica, criterios de docentes, sesiones y calificación."
      width="w-full sm:max-w-2xl"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5 p-4 text-[hsl(var(--foreground))]">
        {/* Tipo de Programa */}
        <div>
          <label className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2 block">
            Tipo de Formación
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {PROGRAM_TYPES.map((t) => {
              const selected = formData.program_type === t.value;
              return (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setFormData({ ...formData, program_type: t.value })}
                  className={clsx(
                    'p-2.5 rounded-lg border text-left transition-all text-xs flex flex-col gap-1',
                    selected
                      ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.08)] shadow-sm'
                      : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary)/0.5)]'
                  )}
                >
                  <span className={clsx('font-bold', selected ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--foreground))]')}>
                    {t.label}
                  </span>
                  <span className="text-[10px] text-[hsl(var(--text-secondary))] line-clamp-1">{t.desc}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Identificación */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-1">
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Código Canónico</label>
            <input
              type="text"
              required
              disabled={!!program}
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              placeholder="EJ: CARR-TEO-01"
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Nombre Institucional</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ej: Licenciatura en Teología Pastoral"
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
            />
          </div>
        </div>

        {/* Nivel y Modalidad */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Nivel / Subtítulo</label>
            <input
              type="text"
              value={formData.level_name}
              onChange={(e) => setFormData({ ...formData, level_name: e.target.value })}
              placeholder="Ej: Pregrado Teológico / Educación Continua"
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Modalidad</label>
            <select
              value={formData.modality}
              onChange={(e) => setFormData({ ...formData, modality: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
            >
              <option value="presencial">Presencial</option>
              <option value="virtual">Virtual (Asincrónico)</option>
              <option value="hibrida">Híbrida / Blended</option>
            </select>
          </div>
        </div>

        {/* Duración y Sesiones */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Unidad de Tiempo</label>
            <select
              value={formData.total_duration_type}
              onChange={(e) => setFormData({ ...formData, total_duration_type: e.target.value })}
              className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            >
              <option value="sesiones">Sesiones de Clase</option>
              <option value="horas">Horas Académicas</option>
              <option value="semanas">Semanas</option>
              <option value="meses">Meses</option>
              <option value="semestres">Semestres</option>
              <option value="anios">Años</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Cantidad Duración</label>
            <input
              type="number"
              min={1}
              value={formData.total_duration_units}
              onChange={(e) => setFormData({ ...formData, total_duration_units: parseInt(e.target.value) || 1 })}
              className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Créditos de Grado</label>
            <input
              type="number"
              min={0}
              value={formData.total_credits}
              onChange={(e) => setFormData({ ...formData, total_credits: parseInt(e.target.value) || 0 })}
              className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
        </div>

        {/* Criterios Docentes & Calificación */}
        <div className="space-y-3 p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
          <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
            Modelo Docente & Criterios Evaluativos
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="flex items-center gap-2 cursor-pointer p-2 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
              <input
                type="checkbox"
                checked={formData.has_teachers}
                onChange={(e) => setFormData({ ...formData, has_teachers: e.target.checked })}
                className="size-4 rounded text-[hsl(var(--primary))]"
              />
              <span className="text-xs font-medium">¿Formación con Docentes?</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer p-2 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
              <input
                type="checkbox"
                checked={formData.teachers_can_grade}
                onChange={(e) => setFormData({ ...formData, teachers_can_grade: e.target.checked })}
                className="size-4 rounded text-[hsl(var(--primary))]"
              />
              <span className="text-xs font-medium">¿Docentes califican notas?</span>
            </label>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-2">
            <div>
              <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Escala Máxima</label>
              <input
                type="number"
                step="0.1"
                min={1}
                value={formData.grading_scale_max}
                onChange={(e) => setFormData({ ...formData, grading_scale_max: parseFloat(e.target.value) || 100.0 })}
                className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Nota Mín. Aprobatoria</label>
              <input
                type="number"
                step="0.1"
                min={0}
                value={formData.min_passing_grade}
                onChange={(e) => setFormData({ ...formData, min_passing_grade: parseFloat(e.target.value) || 70.0 })}
                className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Asistencia Mínima (%)</label>
              <input
                type="number"
                min={0}
                max={100}
                value={formData.min_attendance_percent}
                onChange={(e) => setFormData({ ...formData, min_attendance_percent: parseFloat(e.target.value) || 80.0 })}
                className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
              />
            </div>
          </div>
        </div>

        {/* Descripción */}
        <div>
          <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Descripción o Perfil de Egreso</label>
          <textarea
            rows={3}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Propósito del programa, competencias a adquirir y destinatarios..."
            className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
          />
        </div>

        {/* Botones de Acción */}
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
            <span>{program ? 'Guardar Cambios' : 'Crear Programa'}</span>
          </button>
        </div>
      </form>
    </RightPanel>
  );
}
