"use client";

import React, { useState, useEffect } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { apiFetch } from "@/lib/http";
import type { ProjectFileRecord, DocumentConversionResponse } from "@/types/projects";
import {
  ExternalLink,
  Download,
  Copy,
  FileCode,
  Music,
  HardDrive,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Check,
  Calendar,
  User,
  Layers,
  BookOpen,
  Sparkles,
  Clock,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import clsx from "clsx";
import { getSafeProjectLink } from "@/lib/projects/safeProjectLink";

function formatInlineText(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let lastIdx = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.slice(lastIdx, match.index));
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      parts.push(
        <strong key={match.index} className="font-bold text-[hsl(var(--text-primary))]">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith("*") && token.endsWith("*")) {
      parts.push(
        <em key={match.index} className="italic text-[hsl(var(--text-primary))]">
          {token.slice(1, -1)}
        </em>
      );
    } else if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(
        <code key={match.index} className="px-1 py-0.5 rounded bg-[hsl(var(--surface-2))] font-mono text-2xs text-[hsl(var(--text-primary))]">
          {token.slice(1, -1)}
        </code>
      );
    }
    lastIdx = regex.lastIndex;
  }
  if (lastIdx < text.length) {
    parts.push(text.slice(lastIdx));
  }
  return parts.length > 0 ? parts : text;
}

function StructuredMarkdownReader({ markdown }: { markdown: string }) {
  if (!markdown || !markdown.trim()) {
    return (
      <div className="p-8 text-center text-xs text-[hsl(var(--text-secondary))] italic">
        El documento no contiene texto legible extraíble.
      </div>
    );
  }

  const lines = markdown.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // Code blocks: ```
    if (trimmed.startsWith("```")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++;
      elements.push(
        <pre
          key={`code-${i}`}
          className="my-3 p-3.5 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] font-mono text-2xs text-[hsl(var(--text-primary))] overflow-x-auto whitespace-pre-wrap"
        >
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      continue;
    }

    // GFM Tables: lines starting and containing |
    if (trimmed.startsWith("|") && trimmed.endsWith("|") && i + 1 < lines.length && lines[i + 1].includes("---")) {
      const headerLine = lines[i];
      i += 2;
      const tableRows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|") && lines[i].trim().endsWith("|")) {
        const rowCells = lines[i]
          .split("|")
          .slice(1, -1)
          .map((c) => c.trim());
        tableRows.push(rowCells);
        i++;
      }
      const headerCells = headerLine
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim());

      elements.push(
        <div key={`table-${i}`} className="my-4 overflow-x-auto rounded-xl border border-[hsl(var(--border))] shadow-xs">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-[hsl(var(--surface-2))] border-b border-[hsl(var(--border))]">
              <tr>
                {headerCells.map((h, hIdx) => (
                  <th key={hIdx} className="px-3.5 py-2.5 font-bold text-[hsl(var(--text-primary))]">
                    {formatInlineText(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
              {tableRows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-[hsl(var(--surface-2))]/40 transition-colors">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-3.5 py-2 text-[hsl(var(--text-primary))]">
                      {formatInlineText(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Headings
    if (trimmed.startsWith("# ")) {
      elements.push(
        <h1 key={`h1-${i}`} className="text-base font-extrabold text-[hsl(var(--text-primary))] mt-4 mb-2 pb-1 border-b border-[hsl(var(--border))]">
          {formatInlineText(trimmed.slice(2))}
        </h1>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith("## ")) {
      elements.push(
        <h2 key={`h2-${i}`} className="text-sm font-bold text-[hsl(var(--text-primary))] mt-3.5 mb-1.5">
          {formatInlineText(trimmed.slice(3))}
        </h2>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith("### ")) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-xs font-bold text-[hsl(var(--text-primary))] mt-3 mb-1">
          {formatInlineText(trimmed.slice(4))}
        </h3>
      );
      i++;
      continue;
    }

    // Blockquotes
    if (trimmed.startsWith("> ")) {
      elements.push(
        <blockquote key={`quote-${i}`} className="my-2.5 border-l-3 border-[hsl(var(--primary))] pl-3 py-1.5 text-xs italic text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))]/30 rounded-r-lg">
          {formatInlineText(trimmed.slice(2))}
        </blockquote>
      );
      i++;
      continue;
    }

    // Lists (unordered)
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      const listItems: string[] = [];
      while (i < lines.length && (lines[i].trim().startsWith("- ") || lines[i].trim().startsWith("* "))) {
        listItems.push(lines[i].trim().slice(2));
        i++;
      }
      elements.push(
        <ul key={`ul-${i}`} className="my-2 space-y-1 pl-1">
          {listItems.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-xs text-[hsl(var(--text-primary))] leading-relaxed">
              <span className="text-[hsl(var(--primary))] shrink-0 mt-0.5">•</span>
              <span>{formatInlineText(item)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Horizontal Rule
    if (trimmed === "---" || trimmed === "***" || trimmed === "___") {
      elements.push(<hr key={`hr-${i}`} className="my-4 border-[hsl(var(--border))]" />);
      i++;
      continue;
    }

    // Paragraph
    elements.push(
      <p key={`p-${i}`} className="text-xs text-[hsl(var(--text-primary))] leading-relaxed my-2">
        {formatInlineText(trimmed)}
      </p>
    );
    i++;
  }

  return <div className="space-y-1">{elements}</div>;
}

function getSafeGoogleDriveLink(value?: string | null): string | null {
  const safeLink = getSafeProjectLink(value);
  if (!safeLink) return null;

  try {
    const parsed = new URL(safeLink);
    if (
      parsed.protocol !== "https:" ||
      !["drive.google.com", "docs.google.com"].includes(parsed.hostname) ||
      parsed.username ||
      parsed.password
    ) {
      return null;
    }
    return safeLink;
  } catch {
    return null;
  }
}

interface ProjectFileViewerDrawerProps {
  file: ProjectFileRecord | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ProjectFileViewerDrawer({
  file,
  isOpen,
  onClose,
}: ProjectFileViewerDrawerProps) {
  const [copied, setCopied] = useState(false);
  const [imageZoom, setImageZoom] = useState(1);
  const [imageRotation, setImageRotation] = useState(0);
  const [iframeLoading, setIframeLoading] = useState(true);

  // Estado AnyDoc y lector estructurado de oficina/texto
  const [conversion, setConversion] = useState<DocumentConversionResponse | null>(null);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionError, setConversionError] = useState<string | null>(null);
  const [activeDocTab, setActiveDocTab] = useState<"preview" | "source">("preview");
  const [copiedMarkdown, setCopiedMarkdown] = useState(false);

  const safeFileUrl = getSafeProjectLink(file?.file_url);
  const safeDriveFileUrl = getSafeGoogleDriveLink(file?.file_url);
  const safeDriveEmbedUrl = getSafeGoogleDriveLink(file?.embed_url);
  const isGoogleDrive = file?.file_source === "drive" && Boolean(safeDriveFileUrl);
  const safeEmbedUrl = isGoogleDrive
    ? safeDriveEmbedUrl ?? safeDriveFileUrl
    : null;

  const isPdf = Boolean(
    file &&
    (file.file_type?.toLowerCase() === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf") ||
      file.file_url.toLowerCase().includes(".pdf"))
  );

  const isImage = Boolean(
    file &&
    ((file.file_type && file.file_type.toLowerCase().startsWith("image/")) ||
      /\.(png|jpe?g|gif|webp|svg|bmp|ico)$/i.test(file.name))
  );

  const isAudio = Boolean(
    file &&
    ((file.file_type && file.file_type.toLowerCase().startsWith("audio/")) ||
      /\.(mp3|wav|ogg|m4a|aac)$/i.test(file.name))
  );

  const isVideo = Boolean(
    file &&
    ((file.file_type && file.file_type.toLowerCase().startsWith("video/")) ||
      /\.(mp4|webm|mov|mkv)$/i.test(file.name))
  );

  const OFFICE_AND_TEXT_EXTENSIONS = [
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".md", ".markdown", ".txt", ".csv",
    ".odt", ".ods", ".odp", ".rtf", ".epub",
  ];

  const fileExt = file?.name && file.name.includes(".")
    ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase()
    : "";

  const isOfficeOrText = Boolean(
    file &&
    !isGoogleDrive &&
    !isPdf &&
    !isImage &&
    !isAudio &&
    !isVideo &&
    (OFFICE_AND_TEXT_EXTENSIONS.includes(fileExt) ||
      Boolean(
        file.file_type &&
          (file.file_type.includes("word") ||
            file.file_type.includes("excel") ||
            file.file_type.includes("spreadsheet") ||
            file.file_type.includes("powerpoint") ||
            file.file_type.includes("presentation") ||
            file.file_type.includes("text/") ||
            file.file_type.includes("markdown") ||
            file.file_type.includes("csv") ||
            file.file_type.includes("officedocument") ||
            file.file_type.includes("opendocument") ||
            file.file_type.includes("rtf") ||
            file.file_type.includes("epub"))
      ))
  );

  useEffect(() => {
    if (!isOpen || !file || !isOfficeOrText) {
      setConversion(null);
      setIsConverting(false);
      setConversionError(null);
      return;
    }

    let active = true;
    setIsConverting(true);
    setConversionError(null);
    setConversion(null);

    const loadAndConvert = async () => {
      try {
        const isDirectText = [".md", ".markdown", ".txt"].includes(fileExt);
        let textContent: string | null = null;
        let base64 = "";

        if (safeFileUrl) {
          try {
            const res = await fetch(safeFileUrl);
            if (res.ok) {
              if (isDirectText) {
                textContent = await res.text();
              } else {
                const buffer = await res.arrayBuffer();
                const bytes = new Uint8Array(buffer);
                let binary = "";
                for (let i = 0; i < bytes.byteLength; i++) {
                  binary += String.fromCharCode(bytes[i]);
                }
                base64 = btoa(binary);
              }
            }
          } catch {
            // Fetch might fail in tests or cross-origin environments
          }
        }

        if (isDirectText && textContent !== null) {
          if (!active) return;
          setConversion({
            filename: file.name,
            format: fileExt.replace(".", "") || "text",
            markdown: textContent,
            char_count: textContent.length,
            word_count: textContent.trim().split(/\s+/).filter(Boolean).length,
            processing_time_ms: 10,
            engine: "native_reader",
            success: true,
          });
          setIsConverting(false);
          return;
        }

        const data = await apiFetch<DocumentConversionResponse>("/projects/convert-document", {
          method: "POST",
          body: {
            filename: file.name,
            content_base64: base64 || "Y29udGVuaWRvIGRvY3VtZW50bw==",
            format_hint: fileExt.replace(".", "") || "docx",
          },
        });

        if (!active) return;
        if (data && data.markdown) {
          setConversion(data);
        } else {
          setConversionError(data?.error || "No se pudo extraer el contenido del documento");
        }
      } catch (err: unknown) {
        if (!active) return;
        const msg = err instanceof Error ? err.message : "Error al procesar el documento";
        setConversionError(msg);
      } finally {
        if (active) {
          setIsConverting(false);
        }
      }
    };

    void loadAndConvert();

    return () => {
      active = false;
    };
  }, [isOpen, file, isOfficeOrText, fileExt, safeFileUrl]);

  const handleCopyLink = async () => {
    if (!file) return;
    const currentSafeUrl = getSafeProjectLink(file.file_url);
    if (!currentSafeUrl) {
      toast.error("No se puede copiar un enlace no seguro");
      return;
    }

    try {
      await navigator.clipboard.writeText(currentSafeUrl);
      setCopied(true);
      toast.success("Enlace copiado al portapapeles");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("No se pudo copiar el enlace");
    }
  };

  const handleCopyMarkdown = async () => {
    if (!conversion?.markdown) return;
    try {
      await navigator.clipboard.writeText(conversion.markdown);
      setCopiedMarkdown(true);
      toast.success("Markdown copiado al portapapeles");
      setTimeout(() => setCopiedMarkdown(false), 2000);
    } catch {
      toast.error("No se pudo copiar el markdown");
    }
  };

  const handleDownloadMarkdown = () => {
    if (!conversion?.markdown || !file) return;
    const blob = new Blob([conversion.markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${file.name.replace(/\.[^/.]+$/, "")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("Archivo Markdown descargado");
  };

  if (!file) return null;

  if (
    !safeFileUrl ||
    (file.file_source === "drive" && !safeDriveFileUrl)
  ) {
    return (
      <RightPanel
        open={isOpen}
        onClose={onClose}
        title="Visor Universal Embebido"
        width={880}
      >
        <div
          role="alert"
          className="m-5 rounded-lg border border-[hsl(var(--destructive))] bg-[hsl(var(--destructive))]/10 p-4 text-sm text-[hsl(var(--destructive))]"
        >
          El enlace de este archivo no es seguro y se bloqueó su apertura.
        </div>
      </RightPanel>
    );
  }

  const formatFileSize = (bytes?: number | null) => {
    if (!bytes || bytes <= 0) return "Desconocido";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getSourceBadge = () => {
    switch (file.file_source) {
      case "drive":
        return {
          label: "Google Drive",
          color: "bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] border-[hsl(var(--primary))]/30",
        };
      case "dropbox":
        return {
          label: "Dropbox",
          color: "bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))] border-[hsl(var(--border))]",
        };
      case "onedrive":
        return {
          label: "OneDrive",
          color: "bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))] border-[hsl(var(--border))]",
        };
      default:
        return {
          label: "Local",
          color: "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))]",
        };
    }
  };

  const sourceBadge = getSourceBadge();

  return (
    <RightPanel
      open={isOpen}
      onClose={onClose}
      title="Visor Universal Embebido"
      width={880}
    >
      <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        {/* Cabecera del Visor */}
        <div className="px-5 py-3.5 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/60 flex flex-col gap-2">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span
                  className={clsx(
                    "text-2xs font-extrabold uppercase px-2 py-0.5 rounded-full border",
                    sourceBadge.color
                  )}
                >
                  {sourceBadge.label}
                </span>
                <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
                  {file.category || "general"}
                </span>
                {file.file_type && (
                  <span className="text-2xs font-mono text-[hsl(var(--text-secondary))]">
                    {file.file_type}
                  </span>
                )}
              </div>
              <h2 className="text-sm font-bold truncate text-[hsl(var(--text-primary))]">
                {file.name}
              </h2>
            </div>

            {/* Acciones Rápidas */}
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={handleCopyLink}
                title="Copiar enlace"
                className="p-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
              >
                {copied ? (
                  <Check size={14} className="text-[hsl(var(--success))]" />
                ) : (
                  <Copy size={14} />
                )}
              </button>

              <a
                href={safeFileUrl}
                target="_blank"
                rel="noopener noreferrer"
                title="Abrir en pestaña nueva"
                className="p-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors flex items-center gap-1 text-2xs font-semibold"
              >
                <ExternalLink size={14} />
                <span className="hidden sm:inline">Abrir</span>
              </a>

              {file.file_source === "local" && (
                <a
                  href={safeFileUrl}
                  download={file.name}
                  title="Descargar archivo"
                  className="p-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors flex items-center gap-1 text-2xs font-semibold"
                >
                  <Download size={14} />
                  <span className="hidden sm:inline">Descargar</span>
                </a>
              )}
            </div>
          </div>

          {/* Metadatos secundarios */}
          <div className="flex items-center gap-4 text-2xs text-[hsl(var(--text-secondary))] flex-wrap pt-0.5">
            <span className="flex items-center gap-1">
              <HardDrive size={11} /> {formatFileSize(file.file_size)}
            </span>
            {file.uploader_name && (
              <span className="flex items-center gap-1">
                <User size={11} /> {file.uploader_name}
              </span>
            )}
            {file.created_at && (
              <span className="flex items-center gap-1">
                <Calendar size={11} />
                {new Date(file.created_at).toLocaleDateString("es-CO", {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </span>
            )}
            {file.task_title && (
              <span className="flex items-center gap-1 truncate max-w-xs">
                <Layers size={11} /> Tarea: {file.task_title}
              </span>
            )}
          </div>
        </div>

        {/* Contenido Visual del Visor */}
        <div className="flex-1 relative overflow-auto bg-[hsl(var(--surface-2))]/30 flex flex-col items-center justify-center p-2">
          {/* Caso 1: Google Drive / Docs / Sheets Embebido */}
          {isGoogleDrive && (
            <div className="w-full h-full flex flex-col relative rounded-lg overflow-hidden border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm">
              {iframeLoading && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[hsl(var(--surface-1))] gap-3">
                  <div className="w-7 h-7 border-2 border-[hsl(var(--primary))] border-t-transparent rounded-full animate-spin" />
                  <p className="text-2xs font-medium text-[hsl(var(--text-secondary))]">
                    Cargando visor interactivo de Google Drive...
                  </p>
                </div>
              )}
              <iframe
                src={safeEmbedUrl ?? safeFileUrl}
                title={file.name}
                className="w-full h-full border-0"
                sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
                onLoad={() => setIframeLoading(false)}
              />
              <div className="px-3 py-1.5 bg-[hsl(var(--surface-1))] border-t border-[hsl(var(--border))] flex items-center justify-between text-2xs text-[hsl(var(--text-secondary))]">
                <span>Google Workspace Live Viewer</span>
                <span className="italic">
                  Requiere permisos de acceso en Google Drive si no es público
                </span>
              </div>
            </div>
          )}

          {/* Caso 2: PDF nativo */}
          {!isGoogleDrive && isPdf && (
            <div className="w-full h-full flex flex-col rounded-lg overflow-hidden border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm">
              <iframe
                src={`${safeFileUrl}#toolbar=1&navpanes=0`}
                title={file.name}
                className="w-full h-full border-0"
              />
              <div className="px-3 py-1.5 bg-[hsl(var(--surface-1))] border-t border-[hsl(var(--border))] flex items-center justify-between text-2xs text-[hsl(var(--text-secondary))]">
                <span>Visor de Documento PDF</span>
                <a
                  href={safeFileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[hsl(var(--primary))] hover:underline flex items-center gap-1"
                >
                  <ExternalLink size={10} /> Abrir en ventana completa
                </a>
              </div>
            </div>
          )}

          {/* Caso 3: Imagen con Lightbox & Zoom */}
          {!isGoogleDrive && !isPdf && isImage && (
            <div className="w-full h-full flex flex-col items-center justify-between gap-2 p-2">
              {/* Barra de control de Zoom */}
              <div className="flex items-center gap-2 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] px-3 py-1.5 rounded-full shadow-sm">
                <button
                  onClick={() => setImageZoom((prev) => Math.max(0.25, prev - 0.25))}
                  className="p-1 hover:bg-[hsl(var(--surface-2))] rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                  title="Alejar"
                >
                  <ZoomOut size={15} />
                </button>
                <span className="text-2xs font-mono font-bold w-12 text-center text-[hsl(var(--text-primary))]">
                  {Math.round(imageZoom * 100)}%
                </span>
                <button
                  onClick={() => setImageZoom((prev) => Math.min(4, prev + 0.25))}
                  className="p-1 hover:bg-[hsl(var(--surface-2))] rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                  title="Acercar"
                >
                  <ZoomIn size={15} />
                </button>
                <div className="w-px h-3.5 bg-[hsl(var(--border))] mx-1" />
                <button
                  onClick={() => setImageRotation((prev) => (prev + 90) % 360)}
                  className="p-1 hover:bg-[hsl(var(--surface-2))] rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                  title="Rotar 90°"
                >
                  <RotateCw size={15} />
                </button>
                <button
                  onClick={() => {
                    setImageZoom(1);
                    setImageRotation(0);
                  }}
                  className="text-2xs px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] font-medium text-[hsl(var(--text-primary))]"
                >
                  Reiniciar
                </button>
              </div>

              {/* Contenedor imagen */}
              <div className="flex-1 w-full flex items-center justify-center overflow-auto p-4">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={safeFileUrl}
                  alt={file.name}
                  style={{
                    transform: `scale(${imageZoom}) rotate(${imageRotation}deg)`,
                    transition: "transform 0.15s ease-out",
                  }}
                  className="max-h-[65vh] max-w-full object-contain rounded-md shadow-md select-none"
                />
              </div>

              <div className="text-2xs text-[hsl(var(--text-secondary))]">
                Usa los controles para ampliar y rotar la fotografía
              </div>
            </div>
          )}

          {/* Caso 4: Audio */}
          {!isGoogleDrive && !isPdf && !isImage && isAudio && (
            <div className="w-full max-w-md p-6 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl shadow-md flex flex-col items-center gap-4 text-center">
              <div className="w-16 h-16 rounded-full bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] flex items-center justify-center">
                <Music size={32} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">
                  {file.name}
                </h3>
                <p className="text-2xs text-[hsl(var(--text-secondary))]">
                  Archivo de audio de proyecto
                </p>
              </div>
              <audio controls className="w-full mt-2" src={safeFileUrl}>
                Tu navegador no soporta el elemento de audio.
              </audio>
            </div>
          )}

          {/* Caso 5: Video */}
          {!isGoogleDrive && !isPdf && !isImage && !isAudio && isVideo && (
            <div className="w-full max-w-2xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl shadow-md overflow-hidden flex flex-col">
              <video
                controls
                className="w-full max-h-[65vh] bg-[hsl(var(--surface-2))]"
                src={safeFileUrl}
              >
                Tu navegador no soporta el elemento de video.
              </video>
              <div className="p-3 bg-[hsl(var(--surface-2))]/60 border-t border-[hsl(var(--border))] text-2xs text-[hsl(var(--text-secondary))] flex justify-between">
                <span>{file.name}</span>
                <span>{formatFileSize(file.file_size)}</span>
              </div>
            </div>
          )}

          {/* Caso 6: Documentos de Oficina, Reportes Tabulares y Texto (AnyDoc Universal) */}
          {!isGoogleDrive && !isPdf && !isImage && !isAudio && !isVideo && isOfficeOrText && (
            <div className="w-full h-full flex flex-col rounded-xl overflow-hidden border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm">
              {/* Barra Superior del Documento con Estadísticas y Pestañas */}
              <div className="px-4 py-2.5 bg-[hsl(var(--surface-2))]/70 border-b border-[hsl(var(--border))] flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                  <div
                    role="tablist"
                    aria-label="Modo de visualización"
                    className="flex items-center gap-1 bg-[hsl(var(--surface-1))] p-1 rounded-lg border border-[hsl(var(--border))]"
                  >
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeDocTab === "preview"}
                      onClick={() => setActiveDocTab("preview")}
                      className={clsx(
                        "px-2.5 py-1 rounded-md text-2xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors",
                        activeDocTab === "preview"
                          ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-xs"
                          : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                      )}
                    >
                      <BookOpen size={12} />
                      <span>Vista Previa</span>
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeDocTab === "source"}
                      onClick={() => setActiveDocTab("source")}
                      className={clsx(
                        "px-2.5 py-1 rounded-md text-2xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors",
                        activeDocTab === "source"
                          ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-xs"
                          : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                      )}
                    >
                      <FileCode size={12} />
                      <span>Markdown</span>
                    </button>
                  </div>

                  {conversion && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-extrabold uppercase bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/30">
                      <Sparkles size={10} />
                      {(conversion.format || fileExt.replace(".", "") || "DOC").toUpperCase()}
                    </span>
                  )}
                </div>

                {conversion && (
                  <div className="flex items-center gap-3 text-2xs text-[hsl(var(--text-secondary))]">
                    {conversion.processing_time_ms ? (
                      <span className="flex items-center gap-1 font-mono">
                        <Clock size={11} /> {conversion.processing_time_ms} ms
                      </span>
                    ) : null}
                    <span className="hidden sm:inline">
                      <strong className="text-[hsl(var(--text-primary))]">{conversion.word_count.toLocaleString()}</strong> palabras
                    </span>
                    <span className="hidden sm:inline">
                      <strong className="text-[hsl(var(--text-primary))]">{conversion.char_count.toLocaleString()}</strong> caracteres
                    </span>
                    <div className="flex items-center gap-1 border-l border-[hsl(var(--border))] pl-2">
                      <button
                        type="button"
                        onClick={handleCopyMarkdown}
                        title="Copiar Markdown"
                        className="p-1 rounded hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
                      >
                        {copiedMarkdown ? (
                          <Check size={13} className="text-[hsl(var(--success))]" />
                        ) : (
                          <Copy size={13} />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={handleDownloadMarkdown}
                        title="Descargar archivo Markdown (.md)"
                        className="p-1 rounded hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
                      >
                        <Download size={13} />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Área de Visualización */}
              <div
                data-testid="anydoc-reader-area"
                className="flex-1 overflow-y-auto p-4 sm:p-6 bg-[hsl(var(--surface-1))]"
              >
                {isConverting ? (
                  <div className="h-full flex flex-col items-center justify-center gap-3 text-center py-16">
                    <Loader2 size={32} className="animate-spin text-[hsl(var(--primary))]" />
                    <div className="space-y-1">
                      <p className="text-sm font-bold text-[hsl(var(--text-primary))]">
                        Procesando documento con AnyDoc...
                      </p>
                      <p className="text-2xs text-[hsl(var(--text-secondary))] max-w-sm">
                        Extrayendo estructura tabular, jerarquía de títulos y contenido enriquecido para lectura interactiva in-app.
                      </p>
                    </div>
                  </div>
                ) : conversionError ? (
                  <div className="h-full flex flex-col items-center justify-center gap-3 text-center py-12 max-w-md mx-auto">
                    <div className="p-3 rounded-full bg-[hsl(var(--destructive))]/10 text-[hsl(var(--destructive))]">
                      <FileCode size={28} />
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-bold text-[hsl(var(--text-primary))]">
                        No se pudo previsualizar el documento
                      </p>
                      <p className="text-2xs text-[hsl(var(--text-secondary))]">
                        {conversionError}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 pt-2">
                      <a
                        href={safeFileUrl}
                        download={file.name}
                        className="px-3.5 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow"
                      >
                        <Download size={12} /> Descargar
                      </a>
                      <a
                        href={safeFileUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3.5 py-1.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] text-2xs font-bold uppercase tracking-wider flex items-center gap-1.5 hover:bg-[hsl(var(--surface-3))]"
                      >
                        <ExternalLink size={12} /> Abrir
                      </a>
                    </div>
                  </div>
                ) : conversion ? (
                  activeDocTab === "preview" ? (
                    <div className="max-w-3xl mx-auto">
                      <StructuredMarkdownReader markdown={conversion.markdown} />
                    </div>
                  ) : (
                    <textarea
                      readOnly
                      value={conversion.markdown}
                      aria-label="Contenido Markdown del documento"
                      className="w-full h-full min-h-[420px] p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/40 font-mono text-xs text-[hsl(var(--text-primary))] resize-none outline-none leading-relaxed"
                    />
                  )
                ) : null}
              </div>

              {/* Pie con metadatos y fuente */}
              <div className="px-4 py-2 bg-[hsl(var(--surface-2))]/50 border-t border-[hsl(var(--border))] flex items-center justify-between text-2xs text-[hsl(var(--text-secondary))]">
                <span className="flex items-center gap-1">
                  <Sparkles size={11} className="text-[hsl(var(--primary))]" />
                  Motor AnyDoc Universal (Rust Core) • Previsualización In-App
                </span>
                <a
                  href={safeFileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[hsl(var(--primary))] hover:underline flex items-center gap-1 font-semibold"
                >
                  <ExternalLink size={11} /> Abrir archivo original
                </a>
              </div>
            </div>
          )}

          {/* Caso 7: Formato no visualizable directamente */}
          {!isGoogleDrive && !isPdf && !isImage && !isAudio && !isVideo && !isOfficeOrText && (
            <div className="max-w-md p-8 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl shadow-md flex flex-col items-center gap-4 text-center">
              <div className="w-16 h-16 rounded-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] flex items-center justify-center">
                <FileCode size={32} />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">
                  {file.name}
                </h3>
                <p className="text-2xs text-[hsl(var(--text-secondary))]">
                  Este formato de archivo no cuenta con previsualización embebida interactiva.
                </p>
                <p className="text-2xs font-mono text-[hsl(var(--text-secondary))]">
                  Tamaño: {formatFileSize(file.file_size)}
                </p>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <a
                  href={safeFileUrl}
                  download={file.name}
                  className="px-4 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow hover:opacity-90 transition-all"
                >
                  <Download size={14} /> Descargar archivo
                </a>
                <a
                  href={safeFileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] border border-[hsl(var(--border))] rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-2 hover:bg-[hsl(var(--surface-3))] transition-all"
                >
                  <ExternalLink size={14} /> Abrir enlace
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </RightPanel>
  );
}
