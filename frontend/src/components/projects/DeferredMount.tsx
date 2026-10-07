"use client";

import { useEffect, useState, type ReactNode } from 'react';

interface DeferredMountProps {
  open: boolean;
  children: ReactNode;
}

/** Render a panel only after its first opening, then keep it mounted for close animations/state. */
export function DeferredMount({ open, children }: DeferredMountProps) {
  const [hasOpened, setHasOpened] = useState(open);

  useEffect(() => {
    if (open) setHasOpened(true);
  }, [open]);

  if (!hasOpened) return null;
  return children;
}

export function ProjectDrawerLoading() {
  return (
    <div
      className="fixed inset-0 z-[110] flex justify-end bg-[hsl(var(--surface-1)/0.35)]"
      role="status"
      aria-label="Cargando panel del proyecto"
    >
      <aside className="h-full w-full max-w-xl animate-pulse border-l border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5">
        <div className="mb-5 h-8 w-2/3 rounded-md bg-[hsl(var(--surface-2))]" />
        <div className="mb-3 h-5 rounded-md bg-[hsl(var(--surface-2))]" />
        <div className="h-36 rounded-md bg-[hsl(var(--surface-2))]" />
      </aside>
    </div>
  );
}
