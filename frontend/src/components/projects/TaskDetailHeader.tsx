"use client";

import { ChevronRight, Eye, CheckCircle2, Circle, Loader2, GitBranch, Home, FolderOpen, Paperclip, Star, Maximize2, Trash2, X } from 'lucide-react';
import type { ElementType } from 'react';
import type { ProjectTaskRecord } from '@/types/projects';
import type { TaskStatus } from '@/lib/projects/constants';
import { getStatusOption } from '@/lib/projects/constants';
import clsx from 'clsx';

const STATUS_ICONS: Record<TaskStatus, ElementType> = {
    todo: Circle,
    in_progress: Loader2,
    review: Eye,
    completed: CheckCircle2,
};

function getStatusMap(status: TaskStatus) {
    const opt = getStatusOption(status);
    return { label: opt.label, color: opt.text.split(' ')[0], bg: opt.bg.split(' dark:')[0], icon: STATUS_ICONS[status] };
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
}) {
    const status = getStatusMap((task.status ?? 'todo') as TaskStatus);
    const StatusIcon = status.icon;

    return (
        <header className="shrink-0 px-4 pt-3 pb-0 border-b border-[hsl(var(--border))] dark:border-white/[0.06]">
            {error && (
                <div className="mb-2 rounded-md border border-[hsl(var(--warning)/25%)] bg-warning-soft p-2 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
                    <p className="text-[10px] font-bold uppercase tracking-wide">{error}</p>
                </div>
            )}

            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1 text-[11px] text-[hsl(var(--text-secondary))] min-w-0">
                    <Home size={11} className="shrink-0" />
                    <ChevronRight size={10} className="text-[hsl(var(--text-secondary))] shrink-0" />
                    <FolderOpen size={11} className="shrink-0" />
                    <span className="truncate max-w-[100px] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] cursor-pointer transition-colors">
                        {projectTitle}
                    </span>
                    <ChevronRight size={10} className="text-[hsl(var(--text-secondary))] shrink-0" />
                    <span className="font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] truncate max-w-[120px]">
                        {task.title}
                    </span>
                </div>

                <div className="flex items-center gap-0.5 shrink-0">
                    <button
                        onClick={onVerRutaClick}
                        title="Ver ruta jerárquica"
                        className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold text-[hsl(var(--primary))] bg-info-soft dark:bg-[hsl(var(--info))]/10 hover:bg-[hsl(var(--info-muted))] dark:hover:bg-[hsl(var(--info))]/20 transition-all border border-[hsl(var(--info)/25%)]/50 dark:border-[hsl(var(--info)/100%)]/20"
                    >
                        <GitBranch size={11} />
                        Ver Ruta
                    </button>

                    <button
                        onClick={onFileClick}
                        disabled={uploading}
                        title={uploading ? "Subiendo archivo" : "Adjuntar archivo"}
                        className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all disabled:cursor-wait disabled:opacity-60"
                    >
                        {uploading ? <Loader2 size={14} className="animate-spin" /> : <Paperclip size={14} />}
                    </button>

                    <button
                        onClick={onStarToggle}
                        title={starred ? 'Quitar de favoritos' : 'Marcar como favorito'}
                        className={clsx(
                            'p-1.5 rounded-lg transition-all',
                            starred
                                ? 'text-[hsl(var(--warning))] bg-warning-soft dark:bg-[hsl(var(--warning))]/10'
                                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--warning))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5'
                        )}
                    >
                        <Star size={14} fill={starred ? 'currentColor' : 'none'} />
                    </button>

                    <button
                        title="Expandir a pantalla completa"
                        className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all"
                        onClick={onExpandToggle}
                    >
                        <Maximize2 size={14} />
                    </button>

                    <button
                        onClick={onDeleteTask}
                        title="Eliminar tarea"
                        className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 transition-all"
                    >
                        <Trash2 size={14} />
                    </button>

                    <button
                        onClick={onClose}
                        title="Cerrar panel"
                        className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all ml-0.5"
                    >
                        <X size={14} />
                    </button>
                </div>
            </div>

            <div className="mb-2.5">
                <button
                    onClick={onStatusCycle}
                    title="Click para cambiar estado"
                    className={clsx(
                        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold border border-current/15 transition-all hover:border-current/30 cursor-pointer',
                        status.color, status.bg
                    )}>
                    <StatusIcon size={11} strokeWidth={2.5}
                        className={task.status === 'in_progress' ? 'animate-spin' : ''} />
                    {status.label}
                </button>
            </div>

            <textarea
                value={title}
                onChange={e => onTitleChange(e.target.value)}
                onBlur={onSave}
                rows={1}
                className="w-full text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white bg-transparent resize-none outline-none leading-snug placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] pb-3"
                placeholder="Nombre de la tarea..."
                style={{ minHeight: 28 }}
                onInput={e => {
                    const t = e.currentTarget;
                    t.style.height = 'auto';
                    t.style.height = t.scrollHeight + 'px';
                }}
            />
            {saving && (
                <p className="pb-3 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                    Guardando cambios...
                </p>
            )}
        </header>
    );
}
