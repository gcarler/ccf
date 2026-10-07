'use client';

import { useEffect, useState } from 'react';
import { Save } from 'lucide-react';
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

  return (
    <RightPanel
      open={isOpen}
      onClose={onClose}
      title="Editar proyecto"
      width="w-full sm:max-w-md"
      contentClassName="p-4"
    >
      <div className="space-y-5">
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
