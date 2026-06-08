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
      <div className="size-10 rounded-md bg-slate-100 dark:bg-white/5 flex items-center justify-center">
        <Icon size={36} className="text-slate-300" />
      </div>
      <div className="space-y-2">
        <p className="text-sm font-bold text-slate-600 dark:text-slate-300 tracking-tight">{title}</p>
        <p className="text-sm text-slate-400 max-w-xs">{description}</p>
      </div>
      {action}
    </div>
  );
}
