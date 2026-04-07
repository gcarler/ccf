"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X, Flag, User, Calendar, MoreHorizontal, MessageSquare, Send,
    Trash2, Paperclip, Bell, File as FileIcon, ExternalLink, Loader2,
    Image as ImageIcon, Check, ChevronDown, Sparkles, Tag,
    Circle, CheckCircle2, Clock, Plus, Link2, Maximize2
} from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import * as Popover from '@radix-ui/react-popover';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import type { ProjectTaskRecord, ProjectCommentItem, ProjectAttachment } from '@/types/projects';

interface Props {
    task: ProjectTaskRecord | null;
    isOpen: boolean;
    onClose: () => void;
    onUpdate: (updated: ProjectTaskRecord) => void;
}

// ── Status config ──────────────────────────────────────────────────────────
const STATUS_LIST = [
    { value: 'todo',        label: 'PENDIENTE',   pill: 'bg-slate-100 dark:bg-white/5 text-slate-500 border border-slate-200 dark:border-white/10' },
    { value: 'in_progress', label: 'EN CURSO',    pill: 'bg-violet-600 text-white' },
    { value: 'review',      label: 'REVISIÓN',    pill: 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400' },
    { value: 'done',        label: 'COMPLETADO',  pill: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400' },
    { value: 'blocked',     label: 'BLOQUEADO',   pill: 'bg-rose-100 dark:bg-rose-900/20 text-rose-700 dark:text-rose-400' },
];

const PRIORITY_LIST = [
    { value: 'urgent', label: 'Urgente',  color: 'text-rose-500',   bg: 'bg-rose-50 dark:bg-rose-900/10' },
    { value: 'high',   label: 'Alta',     color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-900/10' },
    { value: 'normal', label: 'Normal',   color: 'text-blue-500',   bg: 'bg-blue-50 dark:bg-blue-900/10' },
    { value: 'low',    label: 'Baja',     color: 'text-slate-400',  bg: 'bg-slate-50 dark:bg-white/5' },
];

function getStatusCfg(value: string) {
    return STATUS_LIST.find(s => s.value === value) ?? STATUS_LIST[0];
}
function getPrioCfg(value: string) {
    return PRIORITY_LIST.find(p => p.value === value) ?? PRIORITY_LIST[2];
}

export default function TaskDetailModal({ task, isOpen, onClose, onUpdate }: Props) {
    const { token, user } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [comments, setComments] = useState<ProjectCommentItem[]>([]);
    const [newComment, setNewComment] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const [isSendingComment, setIsSendingComment] = useState(false);
    const [editingTitle, setEditingTitle] = useState(false);
    const [localTitle, setLocalTitle] = useState('');
    const titleRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (isOpen && task && token) {
            setLocalTitle(task.title);
            fetchComments();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, task, token]);

    const fetchComments = async () => {
        if (!task) return;
        try {
            const data = await apiFetch<ProjectCommentItem[]>(
                `/projects/comments?project_id=${task.project_id}&task_id=${task.id}`,
                { token }
            );
            setComments(data);
        } catch { }
    };

    const handleUpdateField = async (field: string, value: any) => {
        if (!task || !token) return;
        try {
            const updated = await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}`, {
                method: 'PATCH', token,
                body: { [field]: value }
            });
            onUpdate(updated);
            toast.success('Actualizado');
        } catch { toast.error('Error al actualizar'); }
    };

    const handleSendComment = async () => {
        if (!newComment.trim() || !task) return;
        setIsSendingComment(true);
        try {
            await apiFetch(`/projects/comments`, {
                method: 'POST', token,
                body: { project_id: task.project_id, task_id: task.id, content: newComment.trim() }
            });
            setNewComment('');
            fetchComments();
        } catch { toast.error('Error al comentar'); }
        finally { setIsSendingComment(false); }
    };

    const handleFileUpload = async (file: File) => {
        if (!task || !token) return;
        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        try {
            const updated = await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}/attachments`, {
                method: 'POST', token,
                body: formData
            });
            onUpdate(updated);
            toast.success('Adjunto subido');
        } catch { toast.error('Error al subir'); }
        finally { setIsUploading(false); }
    };

    if (!task) return null;

    const statusCfg = getStatusCfg(task.status);
    const prioCfg = getPrioCfg(task.priority ?? 'normal');

    return (
        <Dialog.Root open={isOpen} onOpenChange={open => !open && onClose()}>
            <AnimatePresence>
                {isOpen && (
                    <Dialog.Portal forceMount>
                        {/* Overlay */}
                        <Dialog.Overlay asChild>
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="fixed inset-0 z-[9000] bg-slate-900/30 backdrop-blur-sm"
                            />
                        </Dialog.Overlay>

                        {/* Drawer lateral derecho */}
                        <Dialog.Content asChild>
                            <motion.div
                                initial={{ x: '100%' }}
                                animate={{ x: 0 }}
                                exit={{ x: '100%' }}
                                transition={{ type: 'spring', damping: 28, stiffness: 220 }}
                                onDragOver={e => e.preventDefault()}
                                onDrop={e => { e.preventDefault(); if (e.dataTransfer.files?.[0]) handleFileUpload(e.dataTransfer.files[0]); }}
                                className="fixed right-0 top-0 z-[9001] h-screen w-full max-w-[680px] bg-white dark:bg-[#1e1f21] shadow-2xl border-l border-slate-200 dark:border-white/5 flex flex-col overflow-hidden font-display"
                            >
                                <Dialog.Title className="sr-only">Detalle de tarea</Dialog.Title>
                                <input type="file" ref={fileInputRef} className="hidden"
                                    onChange={e => e.target.files?.[0] && handleFileUpload(e.target.files[0])} />

                                {/* ── HEADER ──────────────────────────────────── */}
                                <header className="flex items-center justify-between px-5 py-3 border-b border-slate-100 dark:border-white/5 shrink-0">
                                    {/* Left: status + breadcrumb */}
                                    <div className="flex items-center gap-2">
                                        {/* Status picker pill */}
                                        <Popover.Root>
                                            <Popover.Trigger asChild>
                                                <button className={clsx(
                                                    'px-2.5 py-1 rounded-md text-[10px] font-black uppercase tracking-wide transition-colors',
                                                    statusCfg.pill
                                                )}>
                                                    {statusCfg.label}
                                                </button>
                                            </Popover.Trigger>
                                            <Popover.Portal>
                                                <Popover.Content sideOffset={6} className="z-[10000] w-44 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-xl shadow-2xl p-1.5">
                                                    {STATUS_LIST.map(s => (
                                                        <button key={s.value} onClick={() => handleUpdateField('status', s.value)}
                                                            className="w-full flex items-center justify-between px-3 py-1.5 text-[11px] font-bold uppercase rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                            <span className={clsx('px-2 py-0.5 rounded-md text-[10px]', s.pill)}>{s.label}</span>
                                                            {task.status === s.value && <Check size={11} className="text-violet-600" />}
                                                        </button>
                                                    ))}
                                                </Popover.Content>
                                            </Popover.Portal>
                                        </Popover.Root>
                                    </div>

                                    {/* Right: actions */}
                                    <div className="flex items-center gap-1">
                                        {isUploading && <Loader2 size={16} className="animate-spin text-violet-600 mr-1" />}
                                        <button onClick={() => fileInputRef.current?.click()}
                                            className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-colors">
                                            <Paperclip size={16} />
                                        </button>
                                        <button className="p-1.5 text-slate-400 hover:text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-500/10 rounded-lg transition-colors">
                                            <Sparkles size={16} />
                                        </button>
                                        <button className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-colors">
                                            <Maximize2 size={16} />
                                        </button>
                                        <button className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors">
                                            <Trash2 size={16} />
                                        </button>
                                        <div className="w-px h-4 bg-slate-200 dark:bg-white/10 mx-1" />
                                        <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-colors">
                                            <X size={17} />
                                        </button>
                                    </div>
                                </header>

                                {/* ── BODY ────────────────────────────────────── */}
                                <div className="flex-1 overflow-y-auto scrollbar-thin">
                                    <div className="px-7 py-5 space-y-5">

                                        {/* Title */}
                                        <div>
                                            <textarea
                                                ref={titleRef}
                                                value={localTitle}
                                                onChange={e => setLocalTitle(e.target.value)}
                                                onBlur={() => { if (localTitle.trim() !== task.title) handleUpdateField('title', localTitle.trim()); }}
                                                rows={2}
                                                className="w-full text-[22px] font-bold text-slate-900 dark:text-white bg-transparent outline-none resize-none leading-snug placeholder:text-slate-300"
                                                placeholder="Nombre de la tarea"
                                            />
                                        </div>

                                        {/* Properties grid — ClickUp style */}
                                        <div className="space-y-0 border border-slate-100 dark:border-white/5 rounded-xl overflow-hidden text-[12px]">
                                            {/* Assigned */}
                                            <PropertyRow label="Persona asignada" icon={User}>
                                                <button className="flex items-center gap-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
                                                    <div className="size-5 rounded-full bg-slate-200 dark:bg-white/10 flex items-center justify-center">
                                                        <User size={11} />
                                                    </div>
                                                    Sin asignar
                                                </button>
                                            </PropertyRow>

                                            {/* Due date */}
                                            <PropertyRow label="Fecha límite" icon={Calendar}>
                                                <button className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors flex items-center gap-1.5">
                                                    <Calendar size={13} />
                                                    {task.due_date
                                                        ? new Date(task.due_date).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })
                                                        : 'Sin fecha límite'
                                                    }
                                                </button>
                                            </PropertyRow>

                                            {/* Priority */}
                                            <PropertyRow label="Prioridad" icon={Flag}>
                                                <Popover.Root>
                                                    <Popover.Trigger asChild>
                                                        <button className={clsx('flex items-center gap-1.5 transition-colors', prioCfg.color)}>
                                                            <Flag size={13} />
                                                            {prioCfg.label}
                                                            <ChevronDown size={11} />
                                                        </button>
                                                    </Popover.Trigger>
                                                    <Popover.Portal>
                                                        <Popover.Content sideOffset={6} className="z-[10000] w-40 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-xl shadow-2xl p-1.5">
                                                            {PRIORITY_LIST.map(p => (
                                                                <button key={p.value} onClick={() => handleUpdateField('priority', p.value)}
                                                                    className="w-full flex items-center justify-between px-3 py-1.5 text-[11px] font-medium rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                                    <span className={clsx('flex items-center gap-1.5', p.color)}>
                                                                        <Flag size={11} />{p.label}
                                                                    </span>
                                                                    {(task.priority ?? 'normal') === p.value && <Check size={11} className="text-violet-600" />}
                                                                </button>
                                                            ))}
                                                        </Popover.Content>
                                                    </Popover.Portal>
                                                </Popover.Root>
                                            </PropertyRow>

                                            {/* Tags */}
                                            <PropertyRow label="Etiquetas" icon={Tag}>
                                                <button className="flex items-center gap-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
                                                    <Plus size={12} />
                                                    Añadir etiqueta
                                                </button>
                                            </PropertyRow>
                                        </div>

                                        {/* Description */}
                                        <div className="space-y-2">
                                            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Descripción</p>
                                            <div className="min-h-[80px] px-4 py-3 rounded-xl border border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02]">
                                                <p
                                                    contentEditable
                                                    suppressContentEditableWarning
                                                    onBlur={e => handleUpdateField('description', e.currentTarget.textContent)}
                                                    className="text-[13px] font-medium text-slate-600 dark:text-slate-300 leading-relaxed outline-none min-h-[60px]"
                                                >
                                                    {task.description || ''}
                                                </p>
                                                {!task.description && (
                                                    <p className="text-[12px] text-slate-300 dark:text-slate-600 pointer-events-none select-none -mt-5">
                                                        Añadir descripción...
                                                    </p>
                                                )}
                                            </div>
                                        </div>

                                        {/* Attachments */}
                                        {(task.attachments?.length ?? 0) > 0 && (
                                            <div className="space-y-2">
                                                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                                                    Adjuntos ({task.attachments?.length})
                                                </p>
                                                <div className="grid grid-cols-2 gap-2">
                                                    {task.attachments?.map(file => (
                                                        <div key={file.id} className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/5 hover:shadow-md transition-all">
                                                            <div className="size-9 rounded-lg bg-slate-200 dark:bg-white/10 flex items-center justify-center text-slate-400 shrink-0">
                                                                <ImageIcon size={16} />
                                                            </div>
                                                            <div className="min-w-0 flex-1">
                                                                <p className="text-[11px] font-bold truncate text-slate-700 dark:text-slate-200">{file.filename}</p>
                                                                <p className="text-[9px] text-slate-400">{((file.file_size ?? 0) / 1024).toFixed(1)} KB</p>
                                                            </div>
                                                            <a href={`http://localhost:8000${file.file_url}`} target="_blank"
                                                                className="p-1 text-slate-300 hover:text-violet-600 transition-colors">
                                                                <ExternalLink size={13} />
                                                            </a>
                                                        </div>
                                                    ))}
                                                    <button onClick={() => fileInputRef.current?.click()}
                                                        className="p-3 border-2 border-dashed border-slate-200 dark:border-white/10 rounded-xl flex items-center justify-center text-slate-300 hover:text-violet-500 hover:border-violet-300 cursor-pointer transition-all">
                                                        <Plus size={18} />
                                                    </button>
                                                </div>
                                            </div>
                                        )}

                                        {/* Comments */}
                                        <div className="space-y-4 pt-2 border-t border-slate-100 dark:border-white/5">
                                            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-4">
                                                Actividad
                                            </p>

                                            {/* Existing comments */}
                                            {comments.map(c => (
                                                <div key={c.id} className="flex gap-3">
                                                    <div className="size-7 rounded-full bg-violet-600 text-white flex items-center justify-center text-[10px] font-black shrink-0">
                                                        {(c.author || 'U').substring(0, 2).toUpperCase()}
                                                    </div>
                                                    <div className="flex-1">
                                                        <p className="text-[11px] font-bold text-slate-700 dark:text-slate-200">{c.author}</p>
                                                        <p className="text-[12px] text-slate-600 dark:text-slate-300 mt-0.5 leading-relaxed">{c.content}</p>
                                                    </div>
                                                </div>
                                            ))}

                                            {/* New comment composer */}
                                            <div className="flex gap-3">
                                                <div className="size-7 rounded-full bg-violet-600 text-white flex items-center justify-center text-[10px] font-black shrink-0">
                                                    {(user?.username || 'U').substring(0, 2).toUpperCase()}
                                                </div>
                                                <div className="flex-1 border border-slate-200 dark:border-white/10 rounded-xl overflow-hidden">
                                                    <textarea
                                                        value={newComment}
                                                        onChange={e => setNewComment(e.target.value)}
                                                        placeholder="Menciona @Brain para crear, encontrar y preguntar lo que quieras"
                                                        rows={2}
                                                        className="w-full px-3 py-2 text-[12px] text-slate-700 dark:text-slate-200 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none resize-none"
                                                    />
                                                    <div className="flex items-center gap-1 px-3 pb-2 border-t border-slate-100 dark:border-white/5 pt-1">
                                                        <button className="flex items-center gap-1 px-2 py-1 rounded text-[11px] font-bold text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                                                            <Plus size={12} />
                                                        </button>
                                                        <button className="flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                                                            Comentario <ChevronDown size={11} />
                                                        </button>
                                                        <div className="flex-1" />
                                                        <button
                                                            onClick={handleSendComment}
                                                            disabled={!newComment.trim() || isSendingComment}
                                                            className={clsx(
                                                                'size-6 rounded-lg flex items-center justify-center transition-all',
                                                                newComment.trim()
                                                                    ? 'bg-violet-600 text-white hover:bg-violet-700'
                                                                    : 'text-slate-300 cursor-not-allowed'
                                                            )}
                                                        >
                                                            {isSendingComment
                                                                ? <Loader2 size={12} className="animate-spin" />
                                                                : <Send size={12} />
                                                            }
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Bottom spacer */}
                                        <div className="h-8" />
                                    </div>
                                </div>
                            </motion.div>
                        </Dialog.Content>
                    </Dialog.Portal>
                )}
            </AnimatePresence>
        </Dialog.Root>
    );
}

// ── Helper components ──────────────────────────────────────────────────────────
function PropertyRow({ label, icon: Icon, children }: {
    label: string;
    icon: React.ElementType;
    children: React.ReactNode;
}) {
    return (
        <div className="flex items-center border-b border-slate-100 dark:border-white/5 last:border-0">
            <div className="w-36 shrink-0 flex items-center gap-2 px-3 py-2.5 text-[11px] font-medium text-slate-400">
                <Icon size={13} />
                {label}
            </div>
            <div className="flex-1 px-3 py-2.5 text-[12px] font-medium text-slate-600 dark:text-slate-300">
                {children}
            </div>
        </div>
    );
}
