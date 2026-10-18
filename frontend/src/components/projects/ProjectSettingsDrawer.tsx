'use client';

import { useEffect, useState } from 'react';
import { Save, ShieldCheck, AlertTriangle, CheckCircle2, Circle } from 'lucide-react';
import clsx from 'clsx';
import RightPanel from '@/components/ui/RightPanel';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { InlineTextArea } from '@/components/ui/inline-editors/InlineTextArea';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import { InlineUserPicker } from '@/components/ui/inline-editors/InlineUserPicker';
import { normalizeProjectColor } from '@/lib/projects/palette';
import { PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT, PROJECT_TITLE_MAX_LENGTH } from '@/lib/projects/constants';
import type { ProjectRecord } from '@/types/projects';

interface ProjectSettingsDrawerProps {
  project: ProjectRecord | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (patch: Partial<ProjectRecord>) => void;
}

export default function ProjectSettingsDrawer({
  project,
  isOpen,
  onClose,
  onSave,
}: ProjectSettingsDrawerProps) {
  const [draft, setDraft] = useState<Partial<ProjectRecord>>({});

  useEffect(() => {
    if (isOpen && project) {
      setDraft({
        title: project.title,
        description: project.description,
        status: project.status,
        owner_id: project.owner_id,
        color: project.color,
      });
    }
  }, [isOpen, project]);

  const handleSave = () => {
    onSave(draft);
    onClose();
  };

  const displayColor = normalizeProjectColor(draft.color);

  const pmiCriteria = [
    {
      key: 'title',
      label: 'Título Oficial',
      met: (draft.title || '').trim().length >= 3,
    },
    {
      key: 'scope',
      label: 'Alcance / Caso de Negocio',
      met: (draft.description || '').trim().length >= 15,
    },
    {
      key: 'status',
      label: 'Estado de Ciclo de Vida',
      met: Boolean(draft.status),
    },
    {
      key: 'owner',
      label: 'Director / Patrocinador (PM)',
      met: Boolean(draft.owner_id),
    },
  ];
  const pmiScore = pmiCriteria.filter(c => c.met).length;
  const isGovernanceComplete = pmiScore === 4;

  const hasCcbRelevantChange = Boolean(
    project &&
      ((draft.status && draft.status !== project.status) ||
        (draft.owner_id ?? null) !== (project.owner_id ?? null))
  );

  return (
    <RightPanel
      open={isOpen}
      onClose={onClose}
      title="Editar proyecto"
      width="w-full sm:max-w-md"
      contentClassName="p-4"
    >
      <div className="space-y-5">
        {/* Tarjeta de Integridad de Gobernanza y Línea Base PMI §4.3 */}
        <div
          data-testid="project-settings-pmi-governance-card"
          className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.5)] p-3 space-y-2.5"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-[hsl(var(--primary))]" />
              <span className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                Integridad de Línea Base PMI §4.3
              </span>
            </div>
            <span
              data-testid="project-settings-pmi-score"
              className={clsx(
                'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-bold border',
                isGovernanceComplete
                  ? 'border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))]'
                  : 'border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))]'
              )}
            >
              <span>{pmiScore}/4 Criterios PMI</span>
              <span>·</span>
              <span>{isGovernanceComplete ? 'Gobernanza Completa' : 'Gobernanza Incompleta'}</span>
            </span>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            {pmiCriteria.map(criterion => (
              <div
                key={criterion.key}
                className={clsx(
                  'flex items-center gap-1.5 rounded-lg border px-2 py-1 text-2xs font-medium',
                  criterion.met
                    ? 'border-[hsl(var(--success)/0.25)] bg-[hsl(var(--success)/0.08)] text-[hsl(var(--foreground))]'
                    : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))]'
                )}
              >
                {criterion.met ? (
                  <CheckCircle2 size={11} className="shrink-0 text-[hsl(var(--success))]" />
                ) : (
                  <Circle size={11} className="shrink-0 text-[hsl(var(--muted-foreground))]" />
                )}
                <span className="truncate">{criterion.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Aviso de Control Integrado de Cambios PMI §4.6 */}
        {hasCcbRelevantChange && (
          <div
            data-testid="project-settings-pmi-ccb-notice"
            className="flex items-start gap-2 rounded-xl border border-[hsl(var(--warning)/0.4)] bg-[hsl(var(--warning)/0.1)] p-3 text-xs text-[hsl(var(--foreground))]"
          >
            <AlertTriangle size={15} className="mt-0.5 shrink-0 text-[hsl(var(--warning))]" />
            <div className="space-y-0.5">
              <p className="font-bold text-[hsl(var(--warning))]">
                Control Integrado de Cambios PMI §4.6 (CCB)
              </p>
              <p className="text-2xs text-[hsl(var(--muted-foreground))] leading-relaxed">
                El cambio de Estado de Ciclo de Vida o Director de Proyecto impacta el Acta de Constitución y debe registrarse en el Comité de Control de Cambios (CCB).
              </p>
            </div>
          </div>
        )}

        <div className="space-y-1">
          <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
            Título
          </label>
          <InlineTextInput
            value={draft.title || ''}
            onChange={v => setDraft(prev => ({ ...prev, title: v }))}
            placeholder="Título del proyecto"
            ariaLabel="Título del proyecto"
            maxLength={PROJECT_TITLE_MAX_LENGTH}
          />
        </div>

        <div className="space-y-1">
          <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
            Descripción
          </label>
          <InlineTextArea
            value={draft.description || ''}
            onChange={v => setDraft(prev => ({ ...prev, description: v }))}
            placeholder="Agregar descripción del proyecto"
            rows={4}
            ariaLabel="Descripción del proyecto"
          />
        </div>

        <div className="space-y-1">
          <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
            Estado
          </label>
          <InlineProjectStatusPicker
            value={draft.status || 'planning'}
            onChange={v => setDraft(prev => ({ ...prev, status: v }))}
          />
        </div>

        <div className="space-y-1">
          <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
            Responsable
          </label>
          <div className="flex items-center gap-2">
            <InlineUserPicker
              endpoint={PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT}
              value={draft.owner_id ?? null}
              onChange={id => setDraft(prev => ({ ...prev, owner_id: id }))}
            />
          </div>
        </div>

        <div className="space-y-1">
          <label
            htmlFor="project-settings-color"
            className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]"
          >
            Color
          </label>
          <div className="flex items-center gap-3">
            <input
              id="project-settings-color"
              type="color"
              aria-label="Color del proyecto"
              value={displayColor}
              onChange={e =>
                setDraft(prev => ({ ...prev, color: e.target.value }))
              }
              className="h-10 w-20 rounded-lg border border-[hsl(var(--border))] bg-transparent cursor-pointer"
            />
            <span className="text-sm font-mono text-[hsl(var(--muted-foreground))]">
              {displayColor}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-5 border-t border-[hsl(var(--border))] pt-4 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))] transition-colors"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all"
        >
          <Save size={14} /> Guardar Cambios
        </button>
      </div>
    </RightPanel>
  );
}
