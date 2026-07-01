"use client";

import React, { useState } from 'react';
import clsx from 'clsx';
import { ChevronDown } from 'lucide-react';

interface PanelSectionProps {
  title: string;
  children: React.ReactNode;
  collapsible?: boolean;
}

export default function PanelSection({ title, children, collapsible }: PanelSectionProps) {
  const [open, setOpen] = useState(true);
  return (
    <div className="space-y-1.5">
      <div
        onClick={() => collapsible && setOpen(v => !v)}
        className={clsx('flex items-center justify-between', collapsible && 'cursor-pointer')}
      >
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
          {title}
        </span>
        {collapsible && (
          <ChevronDown
            size={11}
            className={clsx('text-[hsl(var(--text-secondary))] transition-transform', !open && '-rotate-90')}
          />
        )}
      </div>
      {open && <div className="space-y-1.5">{children}</div>}
    </div>
  );
}
