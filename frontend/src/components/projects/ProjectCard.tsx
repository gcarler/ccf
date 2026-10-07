'use client';

import { CSSProperties } from 'react';
import { ArrowUpRight, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import type { ProjectRecord } from '@/types/projects';
import { useAuth } from '@/context/AuthContext';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import { InlineUserPicker } from '@/components/ui/inline-editors/InlineUserPicker';
import { normalizeProjectColor } from '@/lib/projects/palette';
import { PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT, PROJECT_TITLE_MAX_LENGTH } from '@/lib/projects/constants';
import { canDeleteProject } from '@/lib/projects/access';

function _formatDate(dateStr: string) {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

interface ProjectCardProps {
  project: ProjectRecord;
  index: number;
  onUpdate?: (projectId: string, patch: Partial<ProjectRecord>) => void;
  onDelete?: (projectId: string) => void;
}

export default function ProjectCard({
  project,
  index,
  onUpdate,
  onDelete,
}: ProjectCardProps) {
  const { hasPermission } = useAuth();
  const tasks = Array.isArray(project.tasks) ? project.tasks : [];
  const taskCount = project.task_count ?? tasks.length;
  const completed = project.completed_task_count ?? tasks.filter(t =>
    ['completed', 'completed'].includes((t.status || '').toLowerCase())
  ).length;
  const inProgress = project.in_progress_task_count ?? tasks.filter(t =>
    ['in_progress'].includes((t.status || '').toLowerCase())
  ).length;
  const progress = project.progress_percent ?? (
    taskCount ? Math.round((completed / taskCount) * 100) : 0
  );
  const color = normalizeProjectColor(project.color);
  const canDelete = canDeleteProject(hasPermission);

  return (
      <motion.article
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.04, duration: 0.3 }}
        className="group relative bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] p-3 shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden"
        style={{ '--card-color': color } as CSSProperties}
      >
        {/* Color accent bar top */}
        <div
          className="absolute top-0 left-0 right-0 h-[3px] rounded-t-2xl opacity-80 group-hover:opacity-100 transition-opacity"
          style={{ background: `linear-gradient(90deg, ${color}, ${color}88)` }}
        />

        <div className="space-y-4">
          {/* Header row */}
          <div className="flex items-start justify-between gap-3">
            <label
              className="relative size-6 rounded-md flex items-center justify-center text-[hsl(var(--primary-foreground))] font-black text-lg shadow-lg transition-transform group-hover:scale-105 shrink-0 cursor-pointer overflow-hidden"
              style={{ backgroundColor: color }}
            >
              <input
                type="color"
                value={color}
                aria-label={`Color del proyecto ${project.title}`}
                onChange={e => {
                  onUpdate?.(project.id, { color: e.target.value });
                }}
                className="opacity-0 absolute inset-0 cursor-pointer"
              />
              {project.title.charAt(0)}
            </label>
            <InlineProjectStatusPicker
              value={project.status || 'active'}
              onChange={v => onUpdate?.(project.id, { status: v })}
              size="sm"
            />
          </div>

          {/* Title + description */}
          <div>
            <h3 className="text-sm font-bold text-[hsl(var(--foreground))] leading-snug">
              <InlineTextInput
                value={project.title || ''}
                onChange={v => onUpdate?.(project.id, { title: v })}
                placeholder="Título del proyecto"
                ariaLabel={`Título del proyecto ${project.title}`}
                maxLength={PROJECT_TITLE_MAX_LENGTH}
              />
            </h3>
            <InlineTextInput
              value={project.description || ''}
              onChange={v => onUpdate?.(project.id, { description: v })}
              placeholder="Agregar descripción"
              ariaLabel={`Descripción del proyecto ${project.title}`}
              className="text-sm text-[hsl(var(--muted-foreground))] font-medium mt-1 min-h-[32px]"
              inputClassName="text-sm"
            />
          </div>

          {/* Task stats */}
          {taskCount > 0 && (
            <div className="flex items-center gap-3 text-xs font-medium">
              <span className="flex items-center gap-1 text-[hsl(var(--success))]">
                <span className="size-1.5 rounded-full bg-[hsl(var(--success))] inline-block" />
                {completed} completadas
              </span>
              {inProgress > 0 && (
                <span className="flex items-center gap-1 text-[hsl(var(--primary))]">
                  <span className="size-1.5 rounded-full bg-[hsl(var(--primary))] inline-block" />
                  {inProgress} en curso
                </span>
              )}
              <span className="text-[hsl(var(--muted-foreground))] ml-auto">
                {taskCount} tareas
              </span>
            </div>
          )}

          {/* Progress bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-2xs font-bold text-[hsl(var(--muted-foreground))]">
              <span>Progreso</span>
              <span style={{ color }}>{progress}%</span>
            </div>
            <div
              className="h-1.5 w-full bg-[hsl(var(--surface-2))] rounded-full overflow-hidden"
              role="progressbar"
              aria-label={`Progreso del proyecto ${project.title}`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress}
            >
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{
                  duration: 0.8,
                  delay: index * 0.04 + 0.2,
                  ease: 'easeOut',
                }}
                className="h-full rounded-full"
                style={{ backgroundColor: color }}
              />
            </div>
          </div>

          {/* Footer: date + owner + actions */}
          <div className="flex items-center justify-between pt-1 gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <InlineUserPicker
                endpoint={PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT}
                value={project.owner_id ?? null}
                onChange={id => onUpdate?.(project.id, { owner_id: id })}
              />
              {project.created_at && (
                <span className="text-2xs text-[hsl(var(--muted-foreground))] shrink-0">
                  {new Date(project.created_at).toLocaleDateString('es-PE', {
                    month: 'short',
                    year: 'numeric',
                  })}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <Link
                href={`/plataforma/projects/${project.id}?view=list`}
                aria-label={`Abrir proyecto ${project.title}`}
                className="inline-flex size-9 items-center justify-center rounded-lg text-[hsl(var(--muted-foreground))] transition-colors hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]"
              >
                <ArrowUpRight size={16} aria-hidden="true" />
              </Link>
              {canDelete && onDelete && (
                <button
                  type="button"
                  onClick={e => {
                    e.stopPropagation();
                    onDelete?.(project.id);
                  }}
                  className="p-1.5 rounded-lg text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] transition-colors"
                  title="Eliminar proyecto"
                  aria-label="Eliminar proyecto"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          </div>
        </div>
      </motion.article>
  );
}
