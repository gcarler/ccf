'use client';

import { useMemo, useRef, useState } from 'react';
import { apiFetch } from '@/lib/http';
import type { ProjectAttachment, ProjectFileRecord, ProjectTaskRecord } from '@/types/projects';
import { AlertTriangle, ClipboardCheck, Eye, Loader2, Paperclip, Trash2, Upload } from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { getSafeProjectLink } from '@/lib/projects/safeProjectLink';
import { ProjectFileViewerDrawer } from './ProjectFileViewerDrawer';

type PmiAttachmentCategory = 'QA_EVIDENCE' | 'FORMAL_DOC' | 'VERSIONED';

const PMI_CATEGORY_META: Record<PmiAttachmentCategory, { label: string; pillClass: string }> = {
  FORMAL_DOC: {
    label: 'Entregable Formal',
    pillClass:
      'bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))] border-[hsl(var(--primary)/0.3)]',
  },
  QA_EVIDENCE: {
    label: 'Evidencia QA',
    pillClass:
      'bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.3)]',
  },
  VERSIONED: {
    label: 'Versionado',
    pillClass:
      'bg-[hsl(var(--info-muted))] text-[hsl(var(--info-text))] border-[hsl(var(--info-muted))]'
  },
};

const PMI_FILTER_OPTIONS: { key: PmiAttachmentCategory | 'ALL'; label: string }[] = [
  { key: 'ALL', label: 'Todos' },
  { key: 'FORMAL_DOC', label: 'Entregables Formales' },
  { key: 'QA_EVIDENCE', label: 'Evidencia QA' },
  { key: 'VERSIONED', label: 'Versionados' },
];

const QA_EVIDENCE_IMAGE_PATTERN = /(?:^|[.])\.(png|jpe?g|webp|gif)$/i;
const QA_EVIDENCE_FILENAME_PATTERN = /(evidencia|test|qa|prueba|captura|verificaci)/i;
const FORMAL_DOC_EXT_PATTERN = /(?:^|[.])\.(pdf|docx?|xlsx?|pptx?)$/i;
const FORMAL_DOC_FILENAME_PATTERN = /(acta|informe|reporte|manual|especificaci|entregable|certificado)/i;
const VERSIONED_FILENAME_PATTERN = /(?:^|[\s_-])(?:v\d+(?:\.\d+)?|rev\s*\d+|final)(?:$|[\s_.-])/i;

/** Clasificador PMI §5.5 & §8.3: categoria(s) de control de configuración de un adjunto. */
export function classifyAttachmentPmi(
  attachment: Pick<ProjectAttachment, 'filename' | 'file_type' | 'content_type'>,
): PmiAttachmentCategory[] {
  const filename = attachment?.filename ?? '';
  const mime = `${attachment?.file_type ?? ''} ${attachment?.content_type ?? ''}`;
  const categories: PmiAttachmentCategory[] = [];

  if (
    QA_EVIDENCE_IMAGE_PATTERN.test(filename) ||
    /image\//i.test(mime) ||
    QA_EVIDENCE_FILENAME_PATTERN.test(filename)
  ) {
    categories.push('QA_EVIDENCE');
  }
  if (
    FORMAL_DOC_EXT_PATTERN.test(filename) ||
    FORMAL_DOC_FILENAME_PATTERN.test(filename)
  ) {
    categories.push('FORMAL_DOC');
  }
  if (VERSIONED_FILENAME_PATTERN.test(filename)) {
    categories.push('VERSIONED');
  }
  return categories;
}

const formatAttachmentWeight = (bytes?: number | null) => {
  const total = Number(bytes ?? 0);
  if (total <= 0) return '0 KB';
  if (total < 1024 * 1024) return `${Math.max(1, Math.round(total / 1024))} KB`;
  return `${(total / (1024 * 1024)).toFixed(1)} MB`;
};

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
  // Estabiliza la referencia de adjuntos para memo deps (react-hooks/exhaustive-deps)
  const attachments = useMemo(() => task.attachments ?? [], [task.attachments]);
  const [viewingFile, setViewingFile] = useState<ProjectFileRecord | null>(null);
  const [pmiCategoryFilter, setPmiCategoryFilter] = useState<PmiAttachmentCategory | 'ALL'>('ALL');

  // Auditoría de Configuración del Paquete (PMBOK §5.5 & §8.3)
  const pmiAudit = useMemo(() => {
    const counts = { FORMAL_DOC: 0, QA_EVIDENCE: 0, VERSIONED: 0 } as Record<PmiAttachmentCategory, number>;
    let totalBytes = 0;
    for (const attachment of attachments) {
      totalBytes += Number(attachment.file_size ?? 0);
      for (const category of classifyAttachmentPmi(attachment)) {
        counts[category] += 1;
      }
    }
    return { totalBytes, counts };
  }, [attachments]);

  const visibleAttachments = useMemo(() => {
    if (pmiCategoryFilter === 'ALL') return attachments;
    return attachments.filter((a) => classifyAttachmentPmi(a).includes(pmiCategoryFilter));
  }, [attachments, pmiCategoryFilter]);

  // §5.5 Validar el Alcance: paquete completado sin evidencia adjunta
  const isDeliverableComplete =
    task.status === 'done' || Number(task.physical_progress_pct ?? 0) >= 100;
  const missingEvidenceAlert = isDeliverableComplete && attachments.length === 0;

  const handlePreviewAttachment = (attachment: ProjectAttachment) => {
    setViewingFile({
      id: attachment.id,
      project_id: task.project_id,
      name: attachment.filename,
      category: 'attachments',
      file_source: 'local',
      file_url: attachment.file_url,
      file_type: attachment.file_type ?? undefined,
      file_size: attachment.file_size ?? undefined,
      task_id: task.id,
      task_title: task.title,
      created_at: attachment.created_at ?? new Date().toISOString(),
    });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const MAX_MB = 10;
    const MAX_BYTES = MAX_MB * 1024 * 1024;

    for (const file of Array.from(files)) {
      if (file.size > MAX_BYTES) {
        toast.error(
          `El archivo "${file.name}" supera el límite de ${MAX_MB}MB.`
        );
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
        const updated = await apiFetch<Record<string, unknown>>(
          `/projects/${task.project_id}/tasks/${task.id}/attachments`,
          {
            method: 'POST',
            token: null, // token passed via apiFetch interceptor
            body: formData,
          }
        );
        uploadedCount += 1;
        onUpload({ ...task, ...(updated || {}) });
      } catch {
        toast.error(`Error al subir "${file.name}"`);
      }
    }
    onUploadingChange(false);
    if (uploadedCount > 0)
      toast.success(
        uploadedCount === 1
          ? 'Archivo adjuntado'
          : `${uploadedCount} archivos adjuntados`
      );
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const triggerFileSelection = () => fileInputRef.current?.click();

  return (
    <section
      aria-labelledby="task-attachments-heading"
      className="px-4 py-3 border-b border-[hsl(var(--border))]"
    >
      <div className="mb-3 flex items-center justify-between">
        <h3
          id="task-attachments-heading"
          className="flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]"
        >
          <Paperclip size={11} /> Archivos
          <span className="rounded bg-[hsl(var(--surface-2))] px-1.5 py-0.5 text-2xs font-bold text-[hsl(var(--muted-foreground))]">
            {attachments.length}
          </span>
        </h3>
        {/* QA-003: botón explícito de carga — abre el selector de archivos nativo. */}
        <button
          type="button"
          onClick={triggerFileSelection}
          disabled={uploading}
          title={uploading ? 'Subiendo archivo…' : 'Adjuntar archivo'}
          aria-label={uploading ? 'Subiendo archivos' : 'Adjuntar archivos'}
          aria-busy={uploading}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--info-text))] bg-[hsl(var(--info-muted))] hover:bg-[hsl(var(--info-muted))] transition-colors disabled:cursor-wait disabled:opacity-60"
        >
          {uploading ? (
            <Loader2 size={11} className="animate-spin" />
          ) : (
            <Upload size={11} />
          )}
          {uploading ? 'Subiendo…' : 'Adjuntar'}
        </button>
      </div>

      {missingEvidenceAlert && (
        <div
          data-testid="task-attachments-pmi-missing-evidence-alert"
          role="alert"
          className="mb-2 flex items-start gap-2 rounded-md border border-[hsl(var(--warning)/0.4)] bg-[hsl(var(--warning)/0.1)] px-2.5 py-2 text-2xs text-[hsl(var(--foreground))]"
        >
          <AlertTriangle size={13} className="mt-0.5 shrink-0 text-[hsl(var(--warning))]" />
          <p>
            <span className="font-bold text-[hsl(var(--warning))]">
              Alerta PMI §5.5 (Validar el Alcance):
            </span>{' '}
            Paquete completado sin evidencia documental o entregable verificado adjunto.
          </p>
        </div>
      )}

      {attachments.length > 0 && (
        <div
          data-testid="task-attachments-pmi-audit"
          className="mb-2 space-y-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)] px-2.5 py-2"
        >
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
              <ClipboardCheck size={11} className="text-[hsl(var(--primary))]" />
              Auditoría de Configuración del Paquete
            </span>
            <span className="text-2xs text-[hsl(var(--muted-foreground))] tabular-nums">
              {formatAttachmentWeight(pmiAudit.totalBytes)}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-1.5 text-2xs">
            {(['FORMAL_DOC', 'QA_EVIDENCE', 'VERSIONED'] as PmiAttachmentCategory[]).map((category) => (
              <div
                key={category}
                data-testid={`task-attachments-pmi-count-${category}`}
                className="rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-1.5 py-1 text-center"
              >
                <span className="block text-[hsl(var(--muted-foreground))]">
                  {PMI_CATEGORY_META[category].label}
                </span>
                <span
                  className={clsx(
                    'font-bold',
                    pmiAudit.counts[category] > 0 ? 'text-[hsl(var(--foreground))]' : 'text-[hsl(var(--muted-foreground))]',
                  )}
                >
                  {pmiAudit.counts[category]}
                </span>
              </div>
            ))}
          </div>

          {/* Filtro por categoría PMI (§8.3 ítems de configuración) */}
          <div
            data-testid="task-attachments-pmi-filter"
            className="flex flex-wrap items-center gap-1"
            role="group"
            aria-label="Filtrar adjuntos por categoría PMI"
          >
            {PMI_FILTER_OPTIONS.map((option) => {
              const isActive = pmiCategoryFilter === option.key;
              return (
                <button
                  key={option.key}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() => setPmiCategoryFilter(option.key)}
                  className={clsx(
                    'rounded-md border px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide transition-colors',
                    isActive
                      ? 'border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]'
                      : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] opacity-70 hover:opacity-100',
                  )}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {attachments.length === 0 ? (
        <p className="text-xs italic text-[hsl(var(--muted-foreground))]">
          Sin archivos adjuntos aun.
        </p>
      ) : visibleAttachments.length === 0 ? (
        <p className="rounded-md border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)] px-2.5 py-2 text-center text-2xs text-[hsl(var(--muted-foreground))]">
          No hay adjuntos de la categoría PMI seleccionada.
        </p>
      ) : (
        <div className="space-y-2">
          {visibleAttachments.map(attachment => {
            const fileUrl = getSafeProjectLink(attachment.file_url);
            const pmiCategories = classifyAttachmentPmi(attachment);
            return (
              <div
                key={attachment.id}
                className="flex items-center justify-between gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2"
              >
                <div className="min-w-0 flex-1 text-left">
                  {fileUrl ? (
                    <button
                      type="button"
                      onClick={() => handlePreviewAttachment(attachment)}
                      title={`Previsualizar ${attachment.filename}`}
                      className="truncate text-sm font-bold text-[hsl(var(--foreground))] hover:text-[hsl(var(--primary))] text-left transition-colors cursor-pointer block max-w-full"
                    >
                      {attachment.filename}
                    </button>
                  ) : (
                    <p className="truncate text-sm font-bold text-[hsl(var(--foreground))]">
                      {attachment.filename}
                    </p>
                  )}
                  <p className="text-2xs text-[hsl(var(--muted-foreground))]">
                    {attachment.file_size
                      ? `${Math.max(1, Math.round(attachment.file_size / 1024))} KB`
                      : 'Archivo adjunto'}
                  </p>
                  <span
                    data-testid={`task-attachment-pmi-badge-${attachment.id}`}
                    className="mt-0.5 flex flex-wrap gap-1"
                  >
                    {pmiCategories.length > 0 ? (
                      pmiCategories.map((category) => (
                        <span
                          key={category}
                          className={clsx(
                            'rounded border px-1.5 py-0.5 text-2xs font-semibold',
                            PMI_CATEGORY_META[category].pillClass,
                          )}
                        >
                          {PMI_CATEGORY_META[category].label}
                        </span>
                      ))
                    ) : (
                      <span className="rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-1.5 py-0.5 text-2xs text-[hsl(var(--muted-foreground))]">
                        Adjunto General
                      </span>
                    )}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {fileUrl ? (
                    <>
                      <button
                        type="button"
                        onClick={() => handlePreviewAttachment(attachment)}
                        aria-label={`Previsualizar archivo ${attachment.filename}`}
                        title="Previsualizar archivo"
                        className="inline-flex items-center gap-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] hover:underline px-1.5 py-1 rounded hover:bg-[hsl(var(--surface-2))]"
                      >
                        <Eye size={12} />
                        <span>Previsualizar</span>
                      </button>
                      <a
                        href={fileUrl}
                        target="_blank"
                        rel="noreferrer"
                        aria-label={`Abrir archivo ${attachment.filename} en una pestaña nueva`}
                        className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] hover:underline px-1.5 py-1"
                      >
                        Abrir
                      </a>
                    </>
                  ) : (
                    <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                      Enlace no disponible
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => onDelete(attachment.id)}
                    disabled={deletingAttachmentId === attachment.id}
                    title="Eliminar adjunto"
                    aria-label={`Eliminar archivo ${attachment.filename}`}
                    className="p-1.5 rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] transition-colors disabled:opacity-50"
                  >
                    {deletingAttachmentId === attachment.id ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <Trash2 size={12} />
                    )}
                  </button>
                </div>
              </div>
            );
          })}
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

      <ProjectFileViewerDrawer
        file={viewingFile}
        isOpen={Boolean(viewingFile)}
        onClose={() => setViewingFile(null)}
      />
    </section>
  );
}
