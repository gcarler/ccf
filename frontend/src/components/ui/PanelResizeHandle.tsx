'use client';

import type { useResizablePanel } from '@/hooks/useResizablePanel';

type Props = { resize: ReturnType<typeof useResizablePanel>; label?: string };

export function PanelResizeHandle({
  resize,
  label = 'Ajustar ancho del panel',
}: Props) {
  if (!resize.desktop) return null;
  return (
    <div
      role="separator"
      aria-label={label}
      aria-orientation="vertical"
      aria-valuemin={resize.minWidth}
      aria-valuemax={resize.maxWidth}
      aria-valuenow={Math.round(resize.width)}
      aria-valuetext={`${Math.round(resize.width)} píxeles`}
      tabIndex={0}
      onPointerDown={resize.onPointerDown}
      onKeyDown={resize.onKeyDown}
      onDoubleClick={resize.reset}
      title="Arrastra para ajustar el ancho manualmente. Flechas para ajustar; doble clic para restablecer."
      className="absolute inset-y-0 left-0 z-10 w-2 cursor-col-resize touch-none bg-[hsl(var(--border))]/40 hover:bg-[hsl(var(--primary))]/40 focus-visible:bg-[hsl(var(--primary))]/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[hsl(var(--primary))] before:absolute before:inset-y-0 before:-left-1.5 before:w-5 before:content-['']"
    />
  );
}
