"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { GradingScheme, GradingSchemeCut } from '@/types/academy';
import { Award, Plus, Trash2, Save, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';

interface GradingSchemeDrawerProps {
  open: boolean;
  onClose: () => void;
  scheme: GradingScheme | null;
  token: string | null;
  onSuccess: (saved: GradingScheme) => void;
}

export default function GradingSchemeDrawer({
  open,
  onClose,
  scheme,
  token,
  onSuccess,
}: GradingSchemeDrawerProps) {
  const [submitting, setSubmitting] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [scaleMax, setScaleMax] = useState(100.0);
  const [passingGrade, setPassingGrade] = useState(70.0);
  const [isDefault, setIsDefault] = useState(false);
  const [cuts, setCuts] = useState<GradingSchemeCut[]>([
    { name: 'Primer Corte', order_index: 1, weight_percent: 30.0, description: 'Talleres y primer parcial' },
    { name: 'Segundo Corte', order_index: 2, weight_percent: 30.0, description: 'Actividades y segundo parcial' },
    { name: 'Tercer Corte / Final', order_index: 3, weight_percent: 40.0, description: 'Examen final / Proyecto' },
  ]);

  useEffect(() => {
    if (scheme) {
      setName(scheme.name || '');
      setDescription(scheme.description || '');
      setScaleMax(scheme.scale_max ?? 100.0);
      setPassingGrade(scheme.passing_grade ?? 70.0);
      setIsDefault(scheme.is_default ?? false);
      if (scheme.cuts && scheme.cuts.length > 0) {
        setCuts(
          scheme.cuts.map((c, i) => ({
            name: c.name,
            order_index: c.order_index || i + 1,
            weight_percent: c.weight_percent,
            description: c.description || '',
          }))
        );
      }
    } else {
      setName('');
      setDescription('');
      setScaleMax(100.0);
      setPassingGrade(70.0);
      setIsDefault(false);
      setCuts([
        { name: 'Primer Corte (30%)', order_index: 1, weight_percent: 30.0, description: 'Primer parcial y talleres' },
        { name: 'Segundo Corte (30%)', order_index: 2, weight_percent: 30.0, description: 'Segundo parcial y quices' },
        { name: 'Examen Final / Proyecto (40%)', order_index: 3, weight_percent: 40.0, description: 'Entrega final y sustentación' },
      ]);
    }
  }, [scheme, open]);

  const totalWeight = useMemo(() => {
    return Math.round(cuts.reduce((sum, c) => sum + (c.weight_percent || 0), 0) * 10) / 10;
  }, [cuts]);

  const isValidWeight = Math.abs(totalWeight - 100.0) < 0.05;

  const handleAddCut = () => {
    const nextIdx = cuts.length + 1;
    const remaining = Math.max(0, 100 - totalWeight);
    setCuts([
      ...cuts,
      {
        name: `Corte ${nextIdx}`,
        order_index: nextIdx,
        weight_percent: remaining > 0 ? remaining : 10.0,
        description: '',
      },
    ]);
  };

  const handleRemoveCut = (index: number) => {
    if (cuts.length <= 1) {
      toast.error('Debe haber al menos un corte de calificación');
      return;
    }
    const updated = cuts.filter((_, i) => i !== index).map((c, i) => ({ ...c, order_index: i + 1 }));
    setCuts(updated);
  };

  const handleCutChange = (index: number, field: keyof GradingSchemeCut, value: any) => {
    const updated = [...cuts];
    updated[index] = { ...updated[index], [field]: value };
    setCuts(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (!name.trim()) {
      toast.error('El nombre del esquema es obligatorio');
      return;
    }

    if (!isValidWeight) {
      toast.error(`La suma de los cortes debe ser exactamente 100%. Actualmente es ${totalWeight}%`);
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        name,
        description,
        scale_max: scaleMax,
        passing_grade: passingGrade,
        is_default: isDefault,
        cuts: cuts.map((c, idx) => ({
          name: c.name,
          order_index: idx + 1,
          weight_percent: c.weight_percent,
          description: c.description || null,
        })),
      };

      if (scheme?.id) {
        const updated = await apiFetch<GradingScheme>(`/academy/admin/grading-schemes/${scheme.id}`, {
          method: 'PATCH',
          token,
          body: payload,
        });
        toast.success('Esquema de calificación actualizado');
        onSuccess(updated);
      } else {
        const created = await apiFetch<GradingScheme>('/academy/admin/grading-schemes', {
          method: 'POST',
          token,
          body: payload,
        });
        toast.success('Esquema de calificación creado');
        onSuccess(created);
      }
      onClose();
    } catch (err: unknown) {
      const errorObj = err as { detail?: string; message?: string };
      toast.error(errorObj?.detail || errorObj?.message || 'Error al guardar el esquema');
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
          <span>{scheme ? 'Editar Esquema de Calificación' : 'Nuevo Esquema de Calificación'}</span>
        </div>
      }
      subtitle="Define los cortes de notas (ej. 30%, 30%, 40%) y la escala institucional."
      width="w-full sm:max-w-2xl"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-5 p-4 text-[hsl(var(--foreground))]">
        {/* Datos Principales */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2">
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">
              Nombre del Esquema de Calificación
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej: Semestral Canónico CCF (30% - 30% - 40%)"
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Escala Máxima</label>
            <input
              type="number"
              step="0.1"
              min={1}
              value={scaleMax}
              onChange={(e) => setScaleMax(parseFloat(e.target.value) || 100.0)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1 block">Nota Aprobatoria</label>
            <input
              type="number"
              step="0.1"
              min={0}
              value={passingGrade}
              onChange={(e) => setPassingGrade(parseFloat(e.target.value) || 70.0)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
            />
          </div>
        </div>

        {/* Medidor visual interactivo de suma de cortes */}
        <div className="p-3.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
              Distribución Porcentual Total
            </span>
            <span
              className={clsx(
                'px-2 py-0.5 rounded text-xs font-bold flex items-center gap-1',
                isValidWeight
                  ? 'bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))]'
                  : 'bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))]'
              )}
            >
              {isValidWeight ? <CheckCircle2 className="size-3.5" /> : <AlertCircle className="size-3.5" />}
              {totalWeight}% / 100%
            </span>
          </div>

          {/* Barra de progreso */}
          <div className="w-full h-2.5 rounded-full bg-[hsl(var(--surface-2))] overflow-hidden border border-[hsl(var(--border))]">
            <div
              className={clsx(
                'h-full transition-all duration-300',
                isValidWeight
                  ? 'bg-[hsl(var(--success))]'
                  : totalWeight > 100
                  ? 'bg-[hsl(var(--destructive))]'
                  : 'bg-[hsl(var(--warning))]'
              )}
              style={{ width: `${Math.min(totalWeight, 100)}%` }}
            />
          </div>

          <p className="text-[11px] text-[hsl(var(--text-secondary))]">
            {isValidWeight
              ? '✓ La suma de los pesos porcentuales es exacta (100.0%).'
              : totalWeight < 100
              ? `Falta ${Math.round((100 - totalWeight) * 10) / 10}% para completar el 100.0%.`
              : `Excede por ${Math.round((totalWeight - 100) * 10) / 10}%. Reduce el valor de algún corte.`}
          </p>
        </div>

        {/* Lista de Cortes */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
              Cortes / Notas del Período ({cuts.length})
            </label>
            <button
              type="button"
              onClick={handleAddCut}
              className="px-2.5 py-1 text-xs font-semibold rounded border border-[hsl(var(--primary))] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.08)] flex items-center gap-1 transition-colors"
            >
              <Plus className="size-3.5" />
              <span>Añadir Corte</span>
            </button>
          </div>

          <div className="space-y-2">
            {cuts.map((cut, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex flex-col sm:flex-row gap-2.5 items-start sm:items-center"
              >
                <div className="size-6 rounded bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center justify-center text-xs font-bold text-[hsl(var(--text-secondary))] shrink-0">
                  {idx + 1}
                </div>
                <div className="flex-1 w-full sm:w-auto">
                  <input
                    type="text"
                    required
                    value={cut.name}
                    onChange={(e) => handleCutChange(idx, 'name', e.target.value)}
                    placeholder="Nombre del corte (ej. Primer Corte)"
                    className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]"
                  />
                </div>
                <div className="w-28 shrink-0 flex items-center gap-1">
                  <input
                    type="number"
                    step="0.5"
                    min={0.1}
                    max={100}
                    required
                    value={cut.weight_percent}
                    onChange={(e) => handleCutChange(idx, 'weight_percent', parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1.5 text-xs text-right font-bold rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]"
                  />
                  <span className="text-xs font-bold text-[hsl(var(--text-secondary))]">%</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveCut(idx)}
                  className="p-1.5 text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] rounded transition-colors"
                  title="Eliminar corte"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Esquema por defecto */}
        <label className="flex items-center gap-2 cursor-pointer p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
            className="size-4 rounded text-[hsl(var(--primary))]"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold">Marcar como esquema institucional por defecto</span>
            <span className="text-[11px] text-[hsl(var(--text-secondary))]">
              Se preseleccionará automáticamente al aperturar nuevas materias y comisiones.
            </span>
          </div>
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
            disabled={submitting || !isValidWeight}
            className="px-5 py-2 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center gap-1.5 hover:opacity-90 transition-opacity disabled:opacity-50 shadow-md"
          >
            {submitting ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
            <span>Guardar Esquema</span>
          </button>
        </div>
      </form>
    </RightPanel>
  );
}
