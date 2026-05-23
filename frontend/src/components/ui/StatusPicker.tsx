"use client";

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, ChevronDown } from 'lucide-react';
import clsx from 'clsx';

export interface StatusOption {
    label: string;
    value: string;
    color: string; // Tailwind color class like 'bg-blue-500'
    text: string;  // Tailwind text class like 'text-blue-600'
    bg: string;    // Tailwind light bg class like 'bg-blue-50'
}

interface StatusPickerProps {
    currentValue: string;
    options: StatusOption[];
    onSelect: (newValue: string) => void;
    className?: string;
}

export default function StatusPicker({
    currentValue,
    options,
    onSelect,
    className
}: StatusPickerProps) {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    
    const activeOption = options.find(o => o.value === currentValue) || options[0];

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className={clsx("relative inline-block", className)} ref={containerRef}>
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    setIsOpen(!isOpen);
                }}
                className={clsx(
                    "flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-tight transition-all active:scale-95",
                    activeOption.bg,
                    activeOption.text,
                    "border border-transparent hover:border-current/20"
                )}
            >
                <div className={clsx("w-1.5 h-1.5 rounded-full shrink-0", activeOption.color)} />
                <span>{activeOption.label}</span>
                <ChevronDown size={10} className={clsx("transition-transform duration-200", isOpen && "rotate-180")} />
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 4, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 4, scale: 0.95 }}
                        transition={{ duration: 0.1 }}
                        className="absolute left-0 top-full mt-1 w-40 bg-white dark:bg-[#2a2b2d] rounded-lg shadow-xl border border-slate-200 dark:border-white/10 z-[100] overflow-hidden"
                    >
                        <div className="p-1">
                            {options.map((option) => (
                                <button
                                    key={option.value}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onSelect(option.value);
                                        setIsOpen(false);
                                    }}
                                    className={clsx(
                                        "w-full flex items-center justify-between px-3 py-2 rounded-md text-[11px] font-bold transition-colors",
                                        currentValue === option.value 
                                            ? "bg-slate-100 dark:bg-white/5 text-slate-900 dark:text-white" 
                                            : "text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5"
                                    )}
                                >
                                    <div className="flex items-center gap-2">
                                        <div className={clsx("w-2 h-2 rounded-full", option.color)} />
                                        {option.label}
                                    </div>
                                    {currentValue === option.value && <Check size={12} className="text-blue-500" />}
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
