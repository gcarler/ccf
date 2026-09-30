"use client";

import { useRef } from 'react';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord } from '@/types/projects';
import { Loader2, Paperclip, Trash2, Upload } from 'lucide-react';
import { toast } from 'sonner';

export default function TaskAttachmentSection({
    task,
    uploading,
    deletingAttachmentId,
    onUpload,
    onDelete,
    onUploadingChange,
    externalInputRef,
}: {
    task: ProjectTaskRecord;
    uploading: boolean;
    deletingAttachmentId: string | null;
    onUpload: (updated: ProjectTaskRecord) => void;
    onDelete: (attachmentId: string) => void;
    onUploadingChange: (v: boolean) => void;
    /** Ref compartida con TaskDetailPanel para que el clip del header dispare la selección. */
    externalInputRef?: React.RefObject<HTMLInputElement>;
}) {
    const internalInputRef = useRef<HTMLInputElement>(null);
    const fileInputRef = externalInputRef ?? internalInputRef;
    const attachments = task.attachments ?? [];

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        const MAX_MB = 10;
        const MAX_BYTES = MAX_MB * 1024 * 1024;

        for (const file of Array.from(files)) {
            if (file.size > MAX_BYTES) {
                toast.error(`El archivo "${file.name}" supera el límite de ${MAX_MB}MB.`);
                if (fileInputRef.current) fileInputRef.current.value = '';
                return;
            }
        }

        onUploadingChange(true);
        let uploadedCount = 0;
        for (const file of Array.from(files)) {
            try {
                const formData = new FormData();
                formData.append('file', file);
                const updated = await apiFetch<Record<string, unknown>>(`/projects/${task.project_id}/tasks/${task.id}/attachments`, {
                    method: 'POST',
                    token: null, // token passed via apiFetch interceptor
                    body: formData,
                });
                uploadedCount += 1;
                onUpload({ ...task, ...(updated || {}) });
            } catch {
                toast.error(`Error al subir "${file.name}"`);
            }
        }
        onUploadingChange(false);
        if (uploadedCount > 0) toast.success(uploadedCount === 1 ? 'Archivo adjuntado' : `${uploadedCount} archivos adjuntados`);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const triggerFileSelection = () => fileInputRef.current?.click();

    return (
        <section className="px-4 py-3 border-b border-[hsl(var(--border))]">
            <div className="mb-3 flex items-center justify-between">
                <p className="flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                    <Paperclip size={11} /> Archivos
                    <span className="rounded bg-[hsl(var(--surface-2))] px-1.5 py-0.5 text-2xs font-bold text-[hsl(var(--muted-foreground))]">
                        {attachments.length}
                    </span>
                </p>
                {/* QA-003: botón explícito de carga — abre el selector de archivos nativo. */}
                <button
                    type="button"
                    onClick={triggerFileSelection}
                    disabled={uploading}
                    title={uploading ? 'Subiendo archivo…' : 'Adjuntar archivo'}
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)] hover:bg-[hsl(var(--primary)/0.15)] transition-colors disabled:cursor-wait disabled:opacity-60"
                >
                    {uploading ? <Loader2 size={11} className="animate-spin" /> : <Upload size={11} />}
                    {uploading ? 'Subiendo…' : 'Adjuntar'}
                </button>
            </div>

            {attachments.length === 0 ? (
                <p className="text-xs italic text-[hsl(var(--muted-foreground))]">
                    Sin archivos adjuntos aun.
                </p>
            ) : (
                <div className="space-y-2">
                    {attachments.map(attachment => (
                        <div
                            key={attachment.id}
                            className="flex items-center justify-between gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2"
                        >
                            <a
                                href={attachment.file_url}
                                target="_blank"
                                rel="noreferrer"
                                className="min-w-0 flex-1 text-left transition hover:text-[hsl(var(--primary))]"
                            >
                                <p className="truncate text-sm font-bold text-[hsl(var(--foreground))]">
                                    {attachment.filename}
                                </p>
                                <p className="text-2xs text-[hsl(var(--muted-foreground))]">
                                    {attachment.file_size ? `${Math.max(1, Math.round(attachment.file_size / 1024))} KB` : 'Archivo adjunto'}
                                </p>
                            </a>
                            <div className="flex items-center gap-1 shrink-0">
                                <a
                                    href={attachment.file_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] hover:underline"
                                >
                                    Abrir
                                </a>
                                <button
                                    onClick={() => onDelete(attachment.id)}
                                    disabled={deletingAttachmentId === attachment.id}
                                    title="Eliminar adjunto"
                                    className="p-1.5 rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] transition-colors disabled:opacity-50"
                                >
                                    {deletingAttachmentId === attachment.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handleFileUpload}
                aria-label="Adjuntar archivos a la tarea"
            />
        </section>
    );
}
