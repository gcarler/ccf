"use client";

import { useRef } from 'react';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord } from '@/types/projects';
import { Loader2, Paperclip, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

export default function TaskAttachmentSection({
    task,
    uploading,
    deletingAttachmentId,
    onUpload,
    onDelete,
    onUploadingChange,
}: {
    task: ProjectTaskRecord;
    uploading: boolean;
    deletingAttachmentId: string | null;
    onUpload: (updated: ProjectTaskRecord) => void;
    onDelete: (attachmentId: string) => void;
    onUploadingChange: (v: boolean) => void;
}) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const attachments = task.attachments ?? [];

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        const MAX_MB = 10;
        const MAX_BYTES = MAX_MB * 1024 * 1024;

        for (const file of Array.from(files)) {
            if (file.size > MAX_BYTES) {
                alert(`Error: El archivo "${file.name}" supera el límite de ${MAX_MB}MB.`);
                if (fileInputRef.current) fileInputRef.current.value = '';
                return;
            }
        }

        onUploadingChange(true);
        for (const file of Array.from(files)) {
            try {
                const formData = new FormData();
                formData.append('file', file);
                const updated = await apiFetch<Record<string, unknown>>(`/projects/${task.project_id}/tasks/${task.id}/attachments`, {
                    method: 'POST',
                    token: null, // token passed via apiFetch interceptor
                    body: formData,
                });
                onUpload({ ...task, ...(updated || {}) });
            } catch {
                toast.error('Error al subir archivo');
            }
        }
        onUploadingChange(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    return (
        <section className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.05]">
            <div className="mb-3 flex items-center justify-between">
                <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                    <Paperclip size={11} /> Archivos
                    <span className="rounded bg-[hsl(var(--surface-2))] px-1.5 py-0.5 text-[9px] font-bold text-[hsl(var(--text-secondary))] dark:bg-white/[0.06] dark:text-[hsl(var(--text-secondary))]">
                        {attachments.length}
                    </span>
                </p>
            </div>

            {attachments.length === 0 ? (
                <p className="text-[11px] italic text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                    Sin archivos adjuntos aun.
                </p>
            ) : (
                <div className="space-y-2">
                    {attachments.map(attachment => (
                        <div
                            key={attachment.id}
                            className="flex items-center justify-between gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 dark:border-white/[0.06] dark:bg-white/[0.03]"
                        >
                            <a
                                href={attachment.file_url}
                                target="_blank"
                                rel="noreferrer"
                                className="min-w-0 flex-1 text-left transition hover:text-[hsl(var(--primary))]"
                            >
                                <p className="truncate text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                    {attachment.filename}
                                </p>
                                <p className="text-[10px] text-[hsl(var(--text-secondary))]">
                                    {attachment.file_size ? `${Math.max(1, Math.round(attachment.file_size / 1024))} KB` : 'Archivo adjunto'}
                                </p>
                            </a>
                            <div className="flex items-center gap-1 shrink-0">
                                <a
                                    href={attachment.file_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] hover:underline"
                                >
                                    Abrir
                                </a>
                                <button
                                    onClick={() => onDelete(attachment.id)}
                                    disabled={deletingAttachmentId === attachment.id}
                                    title="Eliminar adjunto"
                                    className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 transition-colors disabled:opacity-50"
                                >
                                    {deletingAttachmentId === attachment.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileUpload} />
        </section>
    );
}
