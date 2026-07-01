'use client';

import React, { ElementType, ReactNode } from 'react';

interface InfoGridItem {
  label: string;
  value: string | ReactNode;
  icon?: ElementType;
}

interface InfoGridProps {
  items: InfoGridItem[];
}

export default function InfoGrid({ items }: InfoGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {items.map((item, i) => (
        <div key={i} className="space-y-1">
          <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{item.label}</p>
          <p className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white flex items-center gap-2">
            {item.icon && <item.icon size={16} className="text-[hsl(var(--primary))] shrink-0" />}
            {item.value || '—'}
          </p>
        </div>
      ))}
    </div>
  );
}
