"use client";

import React, { useState } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import type { ProjectFileRecord } from "@/types/projects";
import {
  ExternalLink,
  Download,
  Copy,
  FileText,
  FileSpreadsheet,
  FileCode,
  Image as ImageIcon,
  Music,
  Video,
  HardDrive,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Check,
  Globe,
  FileCheck2,
  Calendar,
  User,
  Layers,
} from "lucide-react";
import { toast } from "sonner";
import clsx from "clsx";

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

  if (!file) return null;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(file.file_url);
      setCopied(true);
      toast.success("Enlace copiado al portapapeles");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("No se pudo copiar el enlace");
    }
  };

  const isGoogleDrive =
    file.file_source === "drive" ||
    (file.file_url && file.file_url.includes("drive.google.com")) ||
    (file.file_url && file.file_url.includes("docs.google.com"));

  const isPdf =
    file.file_type?.toLowerCase() === "application/pdf" ||
    file.name.toLowerCase().endsWith(".pdf") ||
    file.file_url.toLowerCase().includes(".pdf");

  const isImage =
    (file.file_type && file.file_type.toLowerCase().startsWith("image/")) ||
    /\.(png|jpe?g|gif|webp|svg|bmp|ico)$/i.test(file.name);

  const isAudio =
    (file.file_type && file.file_type.toLowerCase().startsWith("audio/")) ||
    /\.(mp3|wav|ogg|m4a|aac)$/i.test(file.name);

  const isVideo =
    (file.file_type && file.file_type.toLowerCase().startsWith("video/")) ||
    /\.(mp4|webm|mov|mkv)$/i.test(file.name);

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
          color: "bg-[hsl(var(--surface-3))] text-[hsl(var(--foreground))] border-[hsl(var(--border))]",
        };
      case "onedrive":
        return {
          label: "OneDrive",
          color: "bg-[hsl(var(--surface-3))] text-[hsl(var(--foreground))] border-[hsl(var(--border))]",
        };
      default:
        return {
          label: "Local",
          color: "bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]",
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
      <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))]">
        {/* Cabecera del Visor */}
        <div className="px-5 py-3.5 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/60 flex flex-col gap-2">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span
                  className={clsx(
                    "text-3xs font-extrabold uppercase px-2 py-0.5 rounded-full border",
                    sourceBadge.color
                  )}
                >
                  {sourceBadge.label}
                </span>
                <span className="text-3xs font-semibold px-2 py-0.5 rounded-full bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] border border-[hsl(var(--border))]">
                  {file.category || "general"}
                </span>
                {file.file_type && (
                  <span className="text-3xs font-mono text-[hsl(var(--muted-foreground))]">
                    {file.file_type}
                  </span>
                )}
              </div>
              <h2 className="text-sm font-bold truncate text-[hsl(var(--foreground))]">
                {file.name}
              </h2>
            </div>

            {/* Acciones Rápidas */}
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={handleCopyLink}
                title="Copiar enlace"
                className="p-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors"
              >
                {copied ? (
                  <Check size={14} className="text-[hsl(var(--success))]" />
                ) : (
                  <Copy size={14} />
                )}
              </button>

              <a
                href={file.file_url}
                target="_blank"
                rel="noopener noreferrer"
                title="Abrir en pestaña nueva"
                className="p-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors flex items-center gap-1 text-2xs font-semibold"
              >
                <ExternalLink size={14} />
                <span className="hidden sm:inline">Abrir</span>
              </a>

              {file.file_source === "local" && (
                <a
                  href={file.file_url}
                  download={file.name}
                  title="Descargar archivo"
                  className="p-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors flex items-center gap-1 text-2xs font-semibold"
                >
                  <Download size={14} />
                  <span className="hidden sm:inline">Descargar</span>
                </a>
              )}
            </div>
          </div>

          {/* Metadatos secundarios */}
          <div className="flex items-center gap-4 text-3xs text-[hsl(var(--muted-foreground))] flex-wrap pt-0.5">
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
                  <p className="text-2xs font-medium text-[hsl(var(--muted-foreground))]">
                    Cargando visor interactivo de Google Drive...
                  </p>
                </div>
              )}
              <iframe
                src={file.embed_url || file.file_url}
                title={file.name}
                className="w-full h-full border-0"
                sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
                onLoad={() => setIframeLoading(false)}
              />
              <div className="px-3 py-1.5 bg-[hsl(var(--surface-1))] border-t border-[hsl(var(--border))] flex items-center justify-between text-3xs text-[hsl(var(--muted-foreground))]">
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
                src={`${file.file_url}#toolbar=1&navpanes=0`}
                title={file.name}
                className="w-full h-full border-0"
              />
              <div className="px-3 py-1.5 bg-[hsl(var(--surface-1))] border-t border-[hsl(var(--border))] flex items-center justify-between text-3xs text-[hsl(var(--muted-foreground))]">
                <span>Visor de Documento PDF</span>
                <a
                  href={file.file_url}
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
                  className="p-1 hover:bg-[hsl(var(--surface-2))] rounded text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                  title="Alejar"
                >
                  <ZoomOut size={15} />
                </button>
                <span className="text-3xs font-mono font-bold w-12 text-center text-[hsl(var(--foreground))]">
                  {Math.round(imageZoom * 100)}%
                </span>
                <button
                  onClick={() => setImageZoom((prev) => Math.min(4, prev + 0.25))}
                  className="p-1 hover:bg-[hsl(var(--surface-2))] rounded text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                  title="Acercar"
                >
                  <ZoomIn size={15} />
                </button>
                <div className="w-px h-3.5 bg-[hsl(var(--border))] mx-1" />
                <button
                  onClick={() => setImageRotation((prev) => (prev + 90) % 360)}
                  className="p-1 hover:bg-[hsl(var(--surface-2))] rounded text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                  title="Rotar 90°"
                >
                  <RotateCw size={15} />
                </button>
                <button
                  onClick={() => {
                    setImageZoom(1);
                    setImageRotation(0);
                  }}
                  className="text-3xs px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] font-medium text-[hsl(var(--foreground))]"
                >
                  Reiniciar
                </button>
              </div>

              {/* Contenedor imagen */}
              <div className="flex-1 w-full flex items-center justify-center overflow-auto p-4">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={file.file_url}
                  alt={file.name}
                  style={{
                    transform: `scale(${imageZoom}) rotate(${imageRotation}deg)`,
                    transition: "transform 0.15s ease-out",
                  }}
                  className="max-h-[65vh] max-w-full object-contain rounded-md shadow-md select-none"
                />
              </div>

              <div className="text-3xs text-[hsl(var(--muted-foreground))]">
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
                <h3 className="text-sm font-bold text-[hsl(var(--foreground))]">
                  {file.name}
                </h3>
                <p className="text-3xs text-[hsl(var(--muted-foreground))]">
                  Archivo de audio de proyecto
                </p>
              </div>
              <audio controls className="w-full mt-2" src={file.file_url}>
                Tu navegador no soporta el elemento de audio.
              </audio>
            </div>
          )}

          {/* Caso 5: Video */}
          {!isGoogleDrive && !isPdf && !isImage && !isAudio && isVideo && (
            <div className="w-full max-w-2xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl shadow-md overflow-hidden flex flex-col">
              <video
                controls
                className="w-full max-h-[65vh] bg-black"
                src={file.file_url}
              >
                Tu navegador no soporta el elemento de video.
              </video>
              <div className="p-3 bg-[hsl(var(--surface-2))]/60 border-t border-[hsl(var(--border))] text-3xs text-[hsl(var(--muted-foreground))] flex justify-between">
                <span>{file.name}</span>
                <span>{formatFileSize(file.file_size)}</span>
              </div>
            </div>
          )}

          {/* Caso 6: Formato no visualizable directamente */}
          {!isGoogleDrive && !isPdf && !isImage && !isAudio && !isVideo && (
            <div className="max-w-md p-8 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl shadow-md flex flex-col items-center gap-4 text-center">
              <div className="w-16 h-16 rounded-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] flex items-center justify-center">
                <FileCode size={32} />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-[hsl(var(--foreground))]">
                  {file.name}
                </h3>
                <p className="text-2xs text-[hsl(var(--muted-foreground))]">
                  Este formato de archivo no cuenta con previsualización embebida interactiva.
                </p>
                <p className="text-3xs font-mono text-[hsl(var(--muted-foreground))]">
                  Tamaño: {formatFileSize(file.file_size)}
                </p>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <a
                  href={file.file_url}
                  download={file.name}
                  className="px-4 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow hover:opacity-90 transition-all"
                >
                  <Download size={14} /> Descargar archivo
                </a>
                <a
                  href={file.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] border border-[hsl(var(--border))] rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-2 hover:bg-[hsl(var(--surface-3))] transition-all"
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
