"use client";

import { useEffect, useState } from "react";
import { Cloud, Loader2, PencilRuler, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { RightPanel } from "@/components/ui/RightPanel";

export type WhiteboardSaveStatus = "idle" | "saving" | "saved" | "error";

interface Props {
  title: string;
  saveStatus: WhiteboardSaveStatus;
  isDirty: boolean;
  hasConflict?: boolean;
  saveNow: () => void;
  onClose: () => void;
}

export default function ProjectWhiteboardHeader({ title, saveStatus, isDirty, hasConflict = false, saveNow, onClose }: Props) {
  const [confirmClose, setConfirmClose] = useState(false);
  const [closeAfterSave, setCloseAfterSave] = useState(false);
  const [closeSaveFailed, setCloseSaveFailed] = useState(false);

  useEffect(() => {
    if (!closeAfterSave) return;
    if (saveStatus === "error") {
      setCloseAfterSave(false);
      setCloseSaveFailed(true);
      toast.error(hasConflict
        ? "La pizarra cambió en otra sesión. Exporta tus cambios antes de recargar."
        : "No se pudieron guardar los cambios de la pizarra.");
      return;
    }
    if (saveStatus === "saved" && !isDirty) {
      setCloseAfterSave(false);
      setConfirmClose(false);
      onClose();
    }
  }, [closeAfterSave, hasConflict, isDirty, onClose, saveStatus]);

  const requestClose = () => {
    if (isDirty || saveStatus === "saving" || saveStatus === "error") {
      setCloseSaveFailed(false);
      setConfirmClose(true);
      return;
    }
    onClose();
  };

  return (
    <>
      <header className="h-11 px-4 shrink-0 border-b border-[hsl(var(--border))] flex items-center justify-between bg-[hsl(var(--surface-1))] shadow-sm">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-7 items-center justify-center rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]">
            <PencilRuler size={14} />
          </div>
          <span className="truncate text-xs font-bold uppercase tracking-wide text-[hsl(var(--foreground))]">
            {title || "Pizarra del Proyecto"}
          </span>
          <div className="ml-2 flex shrink-0 items-center gap-1.5" role="status" aria-live="polite">
            {saveStatus === "saving" ? (
              <>
                <Loader2 size={10} className="animate-spin text-[hsl(var(--primary))]" />
                <span className="text-2xs font-semibold uppercase text-[hsl(var(--primary))]">Guardando...</span>
              </>
            ) : saveStatus === "error" ? (
              <>
                <Cloud size={10} className="text-[hsl(var(--destructive))]" />
                <span className="text-2xs font-semibold uppercase text-[hsl(var(--destructive))]">Error al guardar</span>
              </>
            ) : saveStatus === "saved" ? (
              <>
                <Cloud size={10} className="text-[hsl(var(--success))]" />
                <span className="text-2xs font-semibold uppercase text-[hsl(var(--success))]">Guardado</span>
              </>
            ) : isDirty ? (
              <>
                <Cloud size={10} className="text-[hsl(var(--warning))]" />
                <span className="text-2xs font-semibold uppercase text-[hsl(var(--warning))]">Sin guardar</span>
              </>
            ) : (
              <>
                <Cloud size={10} className="text-[hsl(var(--success))]" />
                <span className="text-2xs font-semibold uppercase text-[hsl(var(--success))]">Listo</span>
              </>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={saveNow}
            disabled={hasConflict}
            className="flex items-center gap-1.5 rounded-md bg-[hsl(var(--primary))] px-3 py-1.5 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary-foreground))] shadow-md transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Sparkles size={11} /> Guardar
          </button>
          <button
            type="button"
            onClick={requestClose}
            className="rounded-md bg-[hsl(var(--surface-2))] p-1.5 text-[hsl(var(--muted-foreground))] transition-all hover:bg-[hsl(var(--destructive)/0.1)] hover:text-[hsl(var(--destructive))]"
            aria-label="Cerrar pizarra"
            title="Cerrar pizarra"
          >
            <X size={16} />
          </button>
        </div>
      </header>

      <RightPanel
        open={confirmClose}
        onClose={() => setConfirmClose(false)}
        title="Cerrar pizarra"
        description={hasConflict
          ? "La versión guardada cambió desde que abriste esta sesión. Tus cambios locales siguen aquí; expórtalos antes de cerrar y volver a cargar."
          : "Hay cambios que todavía no se han guardado. Guarda antes de cerrar o confirma que quieres descartarlos."}
        width="w-full sm:max-w-md"
      >
        <div className="space-y-4 p-4">
          {closeSaveFailed && (
            <p role="alert" className="rounded-md border border-[hsl(var(--destructive))]/30 bg-[hsl(var(--destructive))]/10 p-3 text-sm text-[hsl(var(--destructive))]">
              {hasConflict
                ? "La pizarra tiene una versión más reciente. No se reintentará automáticamente; exporta tus cambios antes de cerrar y volver a cargar."
                : "No se pudieron guardar los cambios. Puedes reintentar o salir sin guardar."}
            </p>
          )}
          {saveStatus === "saving" && (
            <p role="status" className="text-sm text-[hsl(var(--muted-foreground))]">
              Hay un guardado pendiente o en curso. Puedes esperar a que termine o forzar el guardado de los cambios antes de cerrar.
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              onClick={() => setConfirmClose(false)}
              className="rounded-md border border-[hsl(var(--border))] px-3 py-2 text-sm text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]"
            >
              Seguir editando
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-3 py-2 text-sm text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive))]/10"
            >
              Salir sin guardar
            </button>
            <button
              type="button"
              disabled={hasConflict}
              onClick={() => {
                setCloseSaveFailed(false);
                setCloseAfterSave(true);
                saveNow();
              }}
              className="rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-sm font-semibold text-[hsl(var(--primary-foreground))] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {hasConflict ? "Recarga para guardar" : closeAfterSave ? "Guardando..." : "Guardar y cerrar"}
            </button>
          </div>
        </div>
      </RightPanel>
    </>
  );
}
