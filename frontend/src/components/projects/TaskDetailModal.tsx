"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, CheckCircle2, Clock, Flag, User, Calendar, 
    MoreHorizontal, MessageSquare, Send, Trash2, 
    ChevronRight, Paperclip, Bell, Hash, File, 
    ExternalLink, Loader2, Image as ImageIcon,
    UploadCloud, Download, Check
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

export default function TaskDetailModal({ task, isOpen, onClose, onUpdate }: Props) {
    const { token, user } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [comments, setComments] = useState<ProjectCommentItem[]>([]);
    const [newComment, setNewComment] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);

    useEffect(() => {
        if (isOpen && task && token) {
            fetchComments();
        }
    }, [isOpen, task, token]);

    const fetchComments = async () => {
        if (!task) return;
        try {
            const data = await apiFetch<ProjectCommentItem[]>(`/projects/comments?project_id=${task.project_id}&task_id=${task.id}`, { token });
            setComments(data);
        } catch (err) { console.error(err); }
    };

    const handleUpdateField = async (field: string, value: any) => {
        if (!task || !token) return;
        try {
            const updated = await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}`, {
                method: 'PATCH',
                token,
                body: { [field]: value }
            });
            onUpdate(updated);
            toast.success(`${field.charAt(0).toUpperCase() + field.slice(1)} actualizado`);
        } catch (err) {
            toast.error("Error al actualizar campo");
        }
    };

    const handleFileUpload = async (file: File) => {
        if (!task) return;
        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch(`http://localhost:8000/api/projects/${task.project_id}/tasks/${task.id}/attachments`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });
            if (!response.ok) throw new Error('Error al subir');
            const updatedTask = await response.json();
            onUpdate(updatedTask);
            toast.success(`Evidencia sincronizada`);
        } catch (err) { toast.error("Fallo al subir evidencia"); }
        finally { setIsUploading(false); }
    };

    if (!task) return null;

    return (
        <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <AnimatePresence>
                {isOpen && (
                    <Dialog.Portal forceMount>
                        <Dialog.Overlay asChild>
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[9000] bg-slate-900/40 backdrop-blur-sm" />
                        </Dialog.Overlay>
                        <Dialog.Content asChild>
                            <motion.div 
                                initial={{ opacity: 0, x: 100 }} 
                                animate={{ opacity: 1, x: 0 }} 
                                exit={{ opacity: 0, x: 100 }}
                                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                                onDragLeave={() => setIsDragging(false)}
                                onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files?.[0]) handleFileUpload(e.dataTransfer.files[0]); }}
                                className="fixed right-0 top-0 z-[9001] h-screen w-full max-w-[750px] bg-white dark:bg-[#1e1f21] shadow-2xl border-l border-white/10 flex flex-col overflow-hidden font-display"
                            >
                                <input type="file" ref={fileInputRef} className="hidden" onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])} />

                                {/* Header Ministerial */}
                                <header className="px-8 py-4 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-white/5 shrink-0">
                                    <div className="flex items-center gap-2">
                                        <Hash size={14} className="text-slate-400" />
                                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Misión #{task.id}</span>
                                        <ChevronRight size={12} className="text-slate-300" />
                                        <StatusPicker value={task.status} onChange={(v) => handleUpdateField('status', v)} />
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {isUploading && <Loader2 size={18} className="animate-spin text-blue-600" />}
                                        <button onClick={() => fileInputRef.current?.click()} className="p-2 text-slate-400 hover:text-blue-600 transition-all hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl"><Paperclip size={18} /></button>
                                        <button className="p-2 text-slate-400 hover:text-rose-600 transition-colors"><Trash2 size={18} /></button>
                                        <div className="w-[1px] h-4 bg-slate-200 dark:bg-white/10 mx-1" />
                                        <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-all"><X size={20} /></button>
                                    </div>
                                </header>

                                <div className="flex-1 overflow-y-auto scrollbar-thin p-10 space-y-12">
                                    {/* Title Section */}
                                    <div className="space-y-8">
                                        <h2 className="text-4xl font-black text-slate-900 dark:text-white leading-tight tracking-tight outline-none" contentEditable suppressContentEditableWarning onBlur={(e) => handleUpdateField('title', e.currentTarget.textContent)}>
                                            {task.title}
                                        </h2>
                                        <div className="flex flex-wrap gap-3">
                                            <PriorityPicker value={task.priority} onChange={(v) => handleUpdateField('priority', v)} />
                                            <PropertyBadge label="Entrega" value={task.due_date ? new Date(task.due_date).toLocaleDateString() : 'Sin fecha'} icon={Calendar} color="text-blue-500" bg="bg-blue-50 dark:bg-blue-900/20" />
                                            <PropertyBadge label="Responsable" value="Sin asignar" icon={User} color="text-slate-400" bg="bg-slate-50 dark:bg-white/5" />
                                        </div>
                                    </div>

                                    {/* Description Pro */}
                                    <section className="space-y-4">
                                        <h4 className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">Descripción de la Misión</h4>
                                        <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5 min-h-[150px]">
                                            <p className="text-[14px] font-medium text-slate-600 dark:text-slate-300 leading-relaxed outline-none" contentEditable suppressContentEditableWarning onBlur={(e) => handleUpdateField('description', e.currentTarget.textContent)}>
                                                {task.description || "Haz clic para añadir el alcance detallado de esta tarea."}
                                            </p>
                                        </div>
                                    </section>

                                    {/* Evidencias List */}
                                    <section className="space-y-4">
                                        <h4 className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">Evidencias ({task.attachments?.length || 0})</h4>
                                        <div className="grid grid-cols-2 gap-4">
                                            {task.attachments?.map((file) => (
                                                <div key={file.id} className="flex items-center gap-4 p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-3xl hover:shadow-xl transition-all">
                                                    <div className="size-12 rounded-2xl bg-slate-50 dark:bg-black/20 flex items-center justify-center text-slate-400"><ImageIcon size={24} /></div>
                                                    <div className="min-w-0 flex-1">
                                                        <p className="text-[12px] font-black truncate text-slate-800 dark:text-white">{file.filename}</p>
                                                        <p className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">{(file.file_size || 0 / 1024).toFixed(1)} KB</p>
                                                    </div>
                                                    <a href={`http://localhost:8000${file.file_url}`} target="_blank" className="p-1.5 text-slate-300 hover:text-blue-600 transition-colors"><ExternalLink size={14} /></a>
                                                </div>
                                            ))}
                                            <div onClick={() => fileInputRef.current?.click()} className="p-4 border-2 border-dashed border-slate-100 dark:border-white/5 rounded-3xl flex items-center justify-center text-slate-300 hover:text-blue-500 cursor-pointer bg-slate-50/30 group">
                                                <Plus size={20} className="group-hover:scale-110 transition-transform" />
                                            </div>
                                        </div>
                                    </section>

                                    {/* Comments Placeholder */}
                                    <section className="pt-10 border-t border-slate-100 dark:border-white/5">
                                        <h4 className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400 mb-6">Conversación</h4>
                                        <div className="flex gap-4">
                                            <div className="size-10 rounded-2xl bg-blue-600 flex items-center justify-center text-white font-black text-xs shadow-lg uppercase">{user?.username?.substring(0, 2)}</div>
                                            <textarea placeholder="Escribe un comentario..." className="flex-1 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-6 py-4 text-sm font-medium outline-none resize-none" rows={2} />
                                        </div>
                                    </section>
                                </div>
                            </motion.div>
                        </Dialog.Content>
                    </Dialog.Portal>
                )}
            </AnimatePresence>
        </Dialog.Root>
    );
}

function StatusPicker({ value, onChange }: { value: string, onChange: (v: string) => void }) {
    const statuses = ['todo', 'in_progress', 'review', 'done'];
    return (
        <Popover.Root>
            <Popover.Trigger asChild>
                <button className="flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-900/20 rounded-lg group hover:bg-blue-600 transition-all">
                    <span className="text-[9px] font-black text-blue-600 uppercase group-hover:text-white transition-colors">{value}</span>
                    <ChevronRight size={10} className="text-blue-400 group-hover:text-white transition-colors rotate-90" />
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content sideOffset={5} className="z-[10000] w-48 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl p-2 animate-in fade-in zoom-in-95">
                    {statuses.map(s => (
                        <button key={s} onClick={() => onChange(s)} className="w-full flex items-center justify-between px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 rounded-xl transition-colors">
                            {s} {value === s && <Check size={12} className="text-blue-600" />}
                        </button>
                    ))}
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

function PriorityPicker({ value, onChange }: { value: string, onChange: (v: string) => void }) {
    const priorities = ['low', 'normal', 'high', 'urgent'];
    return (
        <Popover.Root>
            <Popover.Trigger asChild>
                <div className="flex items-center gap-3 bg-slate-50 dark:bg-white/5 px-4 py-2.5 rounded-2xl border border-slate-100 dark:border-white/5 cursor-pointer hover:bg-slate-100 transition-colors group">
                    <Flag size={14} className={value === 'high' || value === 'urgent' ? 'text-rose-500' : 'text-slate-400'} />
                    <div className="flex flex-col">
                        <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest leading-none mb-0.5">Prioridad</span>
                        <span className="text-[11px] font-black text-slate-700 dark:text-slate-200 leading-none uppercase">{value}</span>
                    </div>
                </div>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content sideOffset={5} className="z-[10000] w-48 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl p-2">
                    {priorities.map(p => (
                        <button key={p} onClick={() => onChange(p)} className="w-full flex items-center justify-between px-4 py-2 text-[10px] font-black uppercase text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 rounded-xl">
                            {p} {value === p && <Check size={12} className="text-blue-600" />}
                        </button>
                    ))}
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

function PropertyBadge({ label, value, icon: Icon, color, bg }: any) {
    return (
        <div className={clsx("flex items-center gap-3 px-4 py-2.5 rounded-2xl border border-slate-100 dark:border-white/5", bg)}>
            <Icon size={14} className={color} />
            <div className="flex flex-col">
                <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest leading-none mb-0.5">{label}</span>
                <span className={clsx("text-[11px] font-black uppercase leading-none text-slate-700 dark:text-slate-200")}>{value}</span>
            </div>
        </div>
    );
}
