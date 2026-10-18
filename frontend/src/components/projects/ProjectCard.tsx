'use client';

import { CSSProperties } from 'react';
import { ArrowUpRight, Trash2 } from 'lucide-react';
import clsx from 'clsx';
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

type RagHealth = 'on_track' | 'at_risk' | 'off_track';

const RAG_HEALTH_META: Record<RagHealth, { label: string; className: string }> = {
  on_track: {
    label: 'Salud: En Camino',
    className:
      'bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.3)]',
  },
  at_risk: {
    label: 'Salud: En Riesgo',
    className:
      'bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.4)]',
  },
  off_track: {
    label: 'Salud: Crítico',
    className:
      'bg-[hsl(var(--destructive)/0.12)] text-[hsl(var(--destructive))] border-[hsl(var(--destructive)/0.3)]',
  },
};

/** Deriva el Semáforo RAG PMI: override/status explícito o tareas vencidas pendientes. */
function deriveRagHealth(project: ProjectRecord, tasks: ProjectRecord['tasks']): RagHealth {
  const override = project.health_override;
  const base = override ?? project.health_status;
  if (base === 'on_track' || base === 'at_risk' || base === 'off_track') return base;

  const now = Date.now();
  const overdueCount = (tasks ?? []).filter((task) => {
    const isDone = ['completed', 'done'].includes((task.status || '').toLowerCase());
    return (
      !isDone &&
      Boolean(task.due_date) &&
      new Date(task.due_date as string).getTime() < now
    );
  }).length;
  if (overdueCount > 2) return 'off_track';
  if (overdueCount >= 1) return 'at_risk';
  return 'on_track';
}

/** Franja Ejecutiva de Gobernanza de Portafolio: RAG + BAC/CPI + PM RACI. */
function PortfolioPmiStrip({ project, tasks }: { project: ProjectRecord; tasks: ProjectRecord['tasks'] }) {
  const rag = deriveRagHealth(project, tasks);
  const bac = Number(project.budget_allocated ?? project.budget_summary?.total_budget ?? 0);
  const cpi = project.budget_summary?.cpi;
  const hasPm = Boolean(project.owner_id);

  return (
    <div
      data-testid="project-card-pmi-strip"
      className="flex flex-wrap items-center gap-1.5 text-2xs"
    >
      <span
        data-testid="project-card-pmi-health"
        title="Semaforo de Salud RAG PMI"
        className={clsx(
          'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-semibold',
          RAG_HEALTH_META[rag].className,
        )}
      >
        {RAG_HEALTH_META[rag].label}
      </span>

      <span
        data-testid="project-card-pmi-budget"
        title="Linea Base de Costos BAC & CPI"
        className={clsx(
          'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-semibold tabular-nums',
          bac <= 0
            ? 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]'
            : typeof cpi === 'number' && cpi < 1
              ? 'border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.12)] text-[hsl(var(--destructive))]'
              : 'border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))]',
        )}
      >
        {bac > 0
          ? `BAC $${bac.toLocaleString('es-CO')}${typeof cpi === 'number' ? ` · CPI ${cpi.toFixed(2)}` : ''}`
          : 'Sin Línea Base BAC'}
      </span>

      <span
        data-testid="project-card-pmi-sponsor"
        title="Gobernanza de Responsable / Project Manager (RACI)"
        className={clsx(
          'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-semibold',
          hasPm
            ? 'border-[hsl(var(--success)/0.3)] bg-[hsl(var(--surface-2))] text-[hsl(var(--success))]'
            : 'border-[hsl(var(--warning)/0.4)] bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))]',
        )}
      >
        {hasPm ? 'PM Asignado' : 'Sin PM (RACI)'}
      </span>
    </div>
  );
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
              className="relative size-6 rounded-md flex items-center justify-center text-[hsl(var(--primary-foreground))] font-extrabold text-lg shadow-lg transition-transform group-hover:scale-105 shrink-0 cursor-pointer overflow-hidden"
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

          {/* Franja Ejecutiva de Gobernanza de Portafolio PMI */}
          <PortfolioPmiStrip project={project} tasks={tasks} />

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
