'use client';

import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface FormSectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export default function FormSection({ title, defaultOpen, children }: FormSectionProps) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  return (
    <div className="border border-slate-100 dark:border-white/10 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-white/5 text-[10px] font-bold uppercase tracking-wide text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
      >
        <span>{title}</span>
        <ChevronDown size={14} className={clsx("transition-transform", open && "rotate-180")} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="px-3 py-2 space-y-2"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
