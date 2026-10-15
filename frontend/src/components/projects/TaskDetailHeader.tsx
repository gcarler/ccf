"use client";

import { ChevronRight, Eye, CheckCircle2, Circle, Loader2, GitBranch, Home, FolderOpen, Paperclip, Star, Maximize2, Trash2, X } from 'lucide-react';
import type { ElementType } from 'react';
import { useRouter } from 'next/navigation';
import type { ProjectTaskRecord } from '@/types/projects';
import type { TaskStatus } from '@/lib/projects/constants';
import { getStatusOption } from '@/lib/projects/constants';
import clsx from 'clsx';

function useSafeRouter() {
    try {
        return useRouter();
    } catch {
        return null;
    }
}

const STATUS_ICONS: Record<TaskStatus, ElementType> = {
    todo: Circle,
    in_progress: Loader2,
    review: Eye,
    completed: CheckCircle2,
};

function getStatusMap(status: TaskStatus) {
    const opt = getStatusOption(status);
    return { label: opt.label, color: opt.text.split(' ')[0], bg: opt.bg.split(' ')[0], icon: STATUS_ICONS[status] };
}

export default function TaskDetailHeader({
    task,
    projectTitle,
    title,
    saving,
    uploading,
    starred,
    error,
    onClose,
    onTitleChange,
    onSave,
    onStatusCycle,
    onFileClick,
    onStarToggle,
    onExpandToggle,
    onDeleteTask,
    onVerRutaClick,
    onProjectClick,
    isRouteTreeOpen,
}: {
    task: ProjectTaskRecord;
    projectTitle: string;
    title: string;
    saving: boolean;
    uploading: boolean;
    starred: boolean;
    error: string | null;
    onClose: () => void;
    onTitleChange: (v: string) => void;
    onSave: () => void;
    onStatusCycle: () => void;
    onFileClick: () => void;
    onStarToggle: () => void;
    onExpandToggle: () => void;
    onDeleteTask: () => void;
    onVerRutaClick?: () => void;
    onProjectClick?: () => void;
    isRouteTreeOpen?: boolean;
}) {
    const router = useSafeRouter();
    const status = getStatusMap((task.status ?? 'todo') as TaskStatus);
    const StatusIcon = status.icon;

    const handleVerRutaBtnClick = () => {
        if (onVerRutaClick) {
            onVerRutaClick();
        } else if (task.project_id) {
            router?.push(`/plataforma/projects/${task.project_id}?view=workflow`);
        }
    };

    const handleProjectClick = () => {
        if (onProjectClick) {
            onProjectClick();
        } else if (onVerRutaClick) {
            onVerRutaClick();
            onClose();
        } else if (task.project_id) {
            router?.push(`/plataforma/projects/${task.project_id}`);
        }
    };

    const handleHomeClick = () => {
        router?.push('/plataforma/projects');
    };

    return (
        <header className="shrink-0 px-4 pt-3 pb-0 border-b border-[hsl(var(--border))]">
            {error && (
                <div role="alert" className="mb-2 rounded-md border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-2 text-[hsl(var(--warning))]">
                    <p className="text-2xs font-bold uppercase tracking-wide">{error}</p>
                </div>
            )}

            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1 text-xs text-[hsl(var(--muted-foreground))] min-w-0">
                    <button
                        type="button"
                        onClick={handleHomeClick}
                        title="Ir al listado de proyectos"
                        aria-label="Ir al listado de proyectos"
                        className="p-1 rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] transition-colors inline-flex items-center focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[hsl(var(--primary))]"
                    >
                        <Home size={11} className="shrink-0" />
                    </button>
                    <ChevronRight size={10} className="text-[hsl(var(--muted-foreground))] shrink-0" />
                    <button
                        type="button"
                        onClick={handleProjectClick}
                        title={`Ir al proyecto: ${projectTitle}`}
                        aria-label={`Ir al proyecto: ${projectTitle}`}
                        className="flex items-center gap-1 p-1 rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] transition-colors min-w-0 text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[hsl(var(--primary))]"
                    >
                        <FolderOpen size={11} className="shrink-0" />
                        <span className="truncate max-w-[120px]">
                            {projectTitle}
                        </span>
                    </button>
                    <ChevronRight size={10} className="text-[hsl(var(--muted-foreground))] shrink-0" />
                    <span className="font-semibold text-[hsl(var(--foreground))] truncate max-w-[120px]" title={task.title}>
                        {task.title}
                    </span>
                </div>

                <div className="flex items-center gap-0.5 shrink-0">
                    <button
                        type="button"
                        onClick={handleVerRutaBtnClick}
                        title="Ver ruta jerárquica"
                        aria-label="Ver ruta jerárquica de la actividad"
                        aria-expanded={isRouteTreeOpen}
                        className={clsx(
                            "flex items-center gap-1 px-2 py-1 rounded-lg text-2xs font-bold transition-all border focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[hsl(var(--primary))]",
                            isRouteTreeOpen
                                ? "text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.15)] border-[hsl(var(--primary))]"
                                : "text-[hsl(var(--info-text))] bg-[hsl(var(--info-muted))] hover:bg-[hsl(var(--info-muted))] border-[hsl(var(--primary)/0.2)]"
                        )}
                    >
                        <GitBranch size={11} />
                        Ver Ruta
                    </button>

                    <button
                        onClick={onFileClick}
                        disabled={uploading}
                        title={uploading ? "Subiendo archivo" : "Adjuntar archivo"}
                        aria-label={uploading ? "Subiendo archivo" : "Adjuntar archivo"}
                        className="p-1.5 rounded-lg text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] transition-all disabled:cursor-wait disabled:opacity-60"
                    >
                        {uploading ? <Loader2 size={14} className="animate-spin" /> : <Paperclip size={14} />}
                    </button>

                    <button
                        onClick={onStarToggle}
                        title={starred ? 'Quitar de favoritos' : 'Marcar como favorito'}
                        aria-label={starred ? 'Quitar actividad de favoritos' : 'Marcar actividad como favorita'}
                        className={clsx(
                            'p-1.5 rounded-lg transition-all',
                            starred
                                ? 'text-[hsl(var(--warning))] bg-[hsl(var(--warning)/0.1)]'
                                : 'text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--warning))] hover:bg-[hsl(var(--surface-2))]'
                        )}
                    >
                        <Star size={14} fill={starred ? 'currentColor' : 'none'} />
                    </button>

                    <button
                        title="Expandir a pantalla completa"
                        aria-label="Expandir detalle de actividad"
                        className="p-1.5 rounded-lg text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] transition-all"
                        onClick={onExpandToggle}
                    >
                        <Maximize2 size={14} />
                    </button>

                    <button
                        onClick={onDeleteTask}
                        title="Eliminar actividad"
                        aria-label="Eliminar actividad"
                        className="p-1.5 rounded-lg text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] transition-all"
                    >
                        <Trash2 size={14} />
                    </button>

                    <button
                        onClick={onClose}
                        title="Cerrar panel"
                        aria-label="Cerrar detalle de actividad"
                        className="p-1.5 rounded-lg text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] transition-all ml-0.5"
                    >
                        <X size={14} />
                    </button>
                </div>
            </div>

            <div className="mb-2.5">
                <button
                    onClick={onStatusCycle}
                    title="Click para cambiar estado"
                    aria-label={`Cambiar estado de la actividad. Estado actual: ${status.label}`}
                    className={clsx(
                        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold border border-current/15 transition-all hover:border-current/30 cursor-pointer',
                        status.color, status.bg
                    )}>
                    <StatusIcon size={11} strokeWidth={2.5}
                        className={task.status === 'in_progress' ? 'animate-spin' : ''} />
                    {status.label}
                </button>
            </div>

            <textarea
                aria-label="Título de la actividad"
                value={title}
                onChange={e => onTitleChange(e.target.value)}
                onBlur={onSave}
                rows={1}
                className="w-full min-h-[28px] text-sm font-bold text-[hsl(var(--foreground))] bg-transparent resize-none outline-none leading-snug placeholder:text-[hsl(var(--muted-foreground))] pb-3"
                placeholder="Nombre de la actividad..."
                onInput={e => {
                    const t = e.currentTarget;
                    t.style.height = 'auto';
                    t.style.height = t.scrollHeight + 'px';
                }}
            />
            {saving && (
                <p className="pb-3 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                    Guardando cambios...
                </p>
            )}
        </header>
    );
}
