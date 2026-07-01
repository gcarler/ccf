'use client';

import React from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface HealthIndicatorProps {
  label: string;
  value: number;
  color: string;
}

export default function HealthIndicator({ label, value, color }: HealthIndicatorProps) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
        <span>{label}</span>
        <span className="font-bold text-[hsl(var(--text-primary))] dark:text-white">{value}%</span>
      </div>
      <div className="h-1.5 w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={clsx("h-full rounded-full", color)}
        />
      </div>
    </div>
  );
}
