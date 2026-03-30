"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, CheckCircle2, Clock, Flag, User, Calendar, 
    MoreHorizontal, MessageSquare, Send, Trash2, 
    ChevronRight, Paperclip, Bell, Hash, File, 
    ExternalLink, Loader2, Image as ImageIcon
} from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import type { ProjectTaskRecord, ProjectCommentItem } from '@/types/projects';

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
    const [loadingComments, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen && task && token) {
            fetchComments();
        }
    }, [isOpen, task, token]);

    const fetchComments = async () => {
        if (!task) return;
        setLoading(true);
        try {
            const data = await apiFetch<ProjectCommentItem[]>(`/projects/comments?project_id=${task.project_id}&task_id=${task.id}`, { token });
            setComments(data);
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !task) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            // Nota: Usamos fetch nativo para multipart ya que apiFetch suele estar configurado para JSON
            const response = await fetch(`http://localhost:8000/api/projects/${task.project_id}/tasks/${task.id}/attachments`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            if (!response.ok) throw new Error('Error al subir archivo');
            
            const updatedTask = await response.json();
            onUpdate(updatedTask);
            toast.success(`Archivo "${file.name}" adjuntado`);
        } catch (err) {
            toast.error("Error al subir el archivo");
        } finally {
            setIsUploading(false);
        }
    };

    const handleAddComment = async () => {
        if (!newComment.trim() || !task) return;
        try {
            const created = await apiFetch<ProjectCommentItem>(`/projects/${task.project_id}/comments`, {
                method: 'POST',
                token,
                body: { content: newComment.trim(), task_id: task.id }
            });
            setComments([created, ...comments]);
            setNewComment('');
            toast.success("Comentario añadido");
        } catch (err) { toast.error("Error al comentar"); }
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
                                className="fixed right-0 top-0 z-[9001] h-screen w-full max-w-[700px] bg-white dark:bg-[#1e1f21] shadow-2xl border-l border-white/10 flex flex-col overflow-hidden font-display"
                            >
                                {/* Input oculto para archivos */}
                                <input 
                                    type="file" 
                                    ref={fileInputRef} 
                                    className="hidden" 
                                    onChange={handleFileUpload} 
                                />

                                {/* Header: Context & Actions */}
                                <header className="px-8 py-4 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-white/5">
                                    <div className="flex items-center gap-2">
                                        <Hash size={14} className="text-slate-400" />
                                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Tarea #{task.id}</span>
                                        <ChevronRight size={12} className="text-slate-300" />
                                        <span className="text-[10px] font-black uppercase tracking-widest text-blue-600">Detalles</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        {isUploading && <Loader2 size={18} className="animate-spin text-blue-600" />}
                                        <button className="p-2 text-slate-400 hover:text-slate-600 transition-colors"><Bell size={18} /></button>
                                        <button 
                                            onClick={() => fileInputRef.current?.click()}
                                            className="p-2 text-slate-400 hover:text-blue-600 transition-all hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl"
                                        >
                                            <Paperclip size={18} />
                                        </button>
                                        <button className="p-2 text-slate-400 hover:text-rose-600 transition-colors"><Trash2 size={18} /></button>
                                        <div className="w-[1px] h-4 bg-slate-200 dark:bg-white/10 mx-1" />
                                        <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 transition-colors"><X size={20} /></button>
                                    </div>
                                </header>

                                <div className="flex-1 overflow-y-auto scrollbar-thin p-10 space-y-10">
                                    {/* Task Title & Status */}
                                    <div className="space-y-6">
                                        <div className="flex items-start gap-4">
                                            <div className={clsx(
                                                "mt-1 size-8 rounded-xl flex items-center justify-center border-2",
                                                task.status === 'done' ? "bg-green-500 border-green-500 text-white" : "border-slate-200 dark:border-white/10 text-slate-300"
                                            )}>
                                                {task.status === 'done' && <CheckCircle2 size={18} />}
                                            </div>
                                            <h2 className="text-3xl font-black text-slate-900 dark:text-white leading-tight tracking-tight">{task.title}</h2>
                                        </div>

                                        <div className="flex flex-wrap gap-4 pt-4 border-t border-slate-100 dark:border-white/5">
                                            <Property label="Estado" value={task.status.toUpperCase()} icon={CheckCircle2} color="text-emerald-500" />
                                            <Property label="Prioridad" value={task.priority.toUpperCase()} icon={Flag} color={task.priority === 'high' ? 'text-rose-500' : 'text-slate-400'} />
                                            <Property label="Entrega" value={task.due_date ? new Date(task.due_date).toLocaleDateString() : 'Sin fecha'} icon={Calendar} color="text-blue-500" />
                                        </div>
                                    </div>

                                    {/* Description */}
                                    <section className="space-y-4">
                                        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Descripción</h4>
                                        <div className="p-6 rounded-[2rem] bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5 min-h-[120px]">
                                            <p className="text-[13px] font-medium text-slate-600 dark:text-slate-300 leading-relaxed">
                                                {task.description || "No hay descripción detallada."}
                                            </p>
                                        </div>
                                    </section>

                                    {/* Attachments Section (NUEVO) */}
                                    {task.attachments && task.attachments.length > 0 && (
                                        <section className="space-y-4">
                                            <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Evidencias / Adjuntos</h4>
                                            <div className="grid grid-cols-2 gap-3">
                                                {task.attachments.map((file: any, i: number) => (
                                                    <a 
                                                        key={i} 
                                                        href={`http://localhost:8000${file.url}`} 
                                                        target="_blank" 
                                                        className="flex items-center gap-3 p-3 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-2xl hover:border-blue-500/50 transition-all group"
                                                    >
                                                        <div className="size-10 rounded-xl bg-slate-50 dark:bg-black/20 flex items-center justify-center text-slate-400 group-hover:text-blue-600 transition-colors">
                                                            {file.name.match(/\.(jpg|jpeg|png|gif)$/i) ? <ImageIcon size={18} /> : <File size={18} />}
                                                        </div>
                                                        <div className="min-w-0 flex-1">
                                                            <p className="text-[11px] font-bold truncate text-slate-700 dark:text-slate-200">{file.name}</p>
                                                            <p className="text-[9px] font-medium text-slate-400 uppercase">Adjunto</p>
                                                        </div>
                                                        <ExternalLink size={12} className="text-slate-300 group-hover:text-blue-500" />
                                                    </a>
                                                ))}
                                            </div>
                                        </section>
                                    )}

                                    {/* Checklist / Supplies */}
                                    {task.supplies && task.supplies.length > 0 && (
                                        <section className="space-y-4">
                                            <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Actividades Técnicas</h4>
                                            <div className="space-y-2">
                                                {task.supplies.map(s => (
                                                    <div key={s.id} className="flex items-center gap-3 p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-2xl">
                                                        <div className={clsx("size-4 rounded border-2", s.status === 'ready' ? "bg-green-500 border-green-500" : "border-slate-200")} />
                                                        <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">{s.item_name}</span>
                                                        <span className="ml-auto text-[10px] font-black text-slate-400">×{s.quantity}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </section>
                                    )}

                                    {/* Comments Section */}
                                    <section className="space-y-6 pt-10 border-t border-slate-100 dark:border-white/5">
                                        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2">
                                            <MessageSquare size={14} /> Conversación
                                        </h4>
                                        
                                        <div className="flex gap-4">
                                            <div className="size-10 rounded-2xl bg-blue-600 flex items-center justify-center text-white font-bold text-xs shadow-lg uppercase">
                                                {user?.username?.substring(0, 2)}
                                            </div>
                                            <div className="flex-1 space-y-3">
                                                <textarea 
                                                    value={newComment}
                                                    onChange={(e) => setNewComment(e.target.value)}
                                                    placeholder="Escribe un comentario..."
                                                    className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-[1.5rem] px-5 py-4 text-sm font-medium outline-none focus:ring-4 focus:ring-blue-500/10 transition-all resize-none"
                                                />
                                                <div className="flex justify-end">
                                                    <button 
                                                        onClick={handleAddComment}
                                                        className="px-6 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[11px] font-black uppercase tracking-widest rounded-xl hover:opacity-90 transition-all flex items-center gap-2 shadow-lg shadow-black/10"
                                                    >
                                                        Comentar <Send size={12} />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="space-y-6 pt-6">
                                            {comments.map((c) => (
                                                <div key={c.id} className="flex gap-4 group">
                                                    <div className="size-10 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 font-bold text-xs uppercase">
                                                        {c.author_name.substring(0, 2)}
                                                    </div>
                                                    <div className="flex-1 space-y-1">
                                                        <div className="flex items-center justify-between">
                                                            <span className="text-[12px] font-black text-slate-800 dark:text-white">{c.author_name}</span>
                                                            <span className="text-[10px] font-bold text-slate-400">{new Date(c.created_at).toLocaleDateString()}</span>
                                                        </div>
                                                        <p className="text-[13px] font-medium text-slate-600 dark:text-slate-300 leading-relaxed bg-slate-50 dark:bg-white/5 p-4 rounded-2xl rounded-tl-none border border-slate-100 dark:border-white/5">
                                                            {c.content}
                                                        </p>
                                                    </div>
                                                </div>
                                            ))}
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

function Property({ label, value, icon: Icon, color }: any) {
    return (
        <div className="flex items-center gap-3 bg-slate-50 dark:bg-white/5 px-4 py-2 rounded-2xl border border-slate-100 dark:border-white/5">
            <Icon size={14} className={color} />
            <div className="flex flex-col">
                <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest leading-none mb-0.5">{label}</span>
                <span className="text-[11px] font-black text-slate-700 dark:text-slate-200 leading-none">{value}</span>
            </div>
        </div>
    );
}
