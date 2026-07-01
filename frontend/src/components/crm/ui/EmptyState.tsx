'use client';

import React, { ElementType, ReactNode } from 'react';

interface EmptyStateProps {
  icon: ElementType;
  title: string;
  description: string;
  action?: ReactNode;
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="lg:col-span-12 py-1.5 flex flex-col items-center gap-4 text-center">
      <div className="size-10 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
        <Icon size={36} className="text-[hsl(var(--text-secondary))]" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] tracking-tight">{title}</p>
        <p className="text-sm text-[hsl(var(--text-secondary))] max-w-xs">{description}</p>
      </div>
      {action}
    </div>
  );
}
