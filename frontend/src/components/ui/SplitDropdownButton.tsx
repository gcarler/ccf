"use client";

import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Plus, FileText, Bell, LayoutDashboard, Layout } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface DropdownOption {
    id: string;
    label: string;
    icon?: any;
    onClick?: () => void;
}

interface SplitDropdownButtonProps {
    onMainClick: () => void;
    onOptionClick?: (id: string) => void;
    mainLabel?: string;
    icon?: any;
    options?: DropdownOption[];
}

export default function SplitDropdownButton({ onMainClick, onOptionClick, mainLabel = "Nuevo", icon: Icon, options }: SplitDropdownButtonProps) {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleOption = (id: string, customClick?: () => void) => {
        setIsOpen(false);
        if (customClick) customClick();
        if (onOptionClick) onOptionClick(id);
    };

    // Default project options if none provided
    const defaultOptions: DropdownOption[] = [
        { id: 'task', label: 'Tarea', icon: Plus },
        { id: 'document', label: 'Documento', icon: FileText },
        { id: 'reminder', label: 'Recordatorio', icon: Bell },
        { id: 'whiteboard', label: 'Pizarra', icon: LayoutDashboard },
        { id: 'panel', label: 'Panel', icon: Layout }
    ];

    const displayOptions = options || defaultOptions;

    return (
        <div className="relative inline-flex items-center ml-2" ref={dropdownRef}>
            {/* Split Button Container — usa variables del tema en vez de colores fijos oscuros */}
            <div className="flex items-center bg-[hsl(var(--primary))] hover:opacity-90 text-white rounded-[7px] overflow-hidden transition-all shadow-sm">

                {/* Main Action */}
                <button
                    onClick={onMainClick}
                    className="h-7 px-3 text-[11px] font-bold flex items-center gap-1.5 transition-colors border-r border-white/20 active:bg-white/15 whitespace-nowrap"
                >
                    {Icon && <Icon size={12} />}
                    {mainLabel}
                </button>

                {/* Dropdown Chevron */}
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="h-7 w-7 flex items-center justify-center transition-colors hover:bg-white/15 active:bg-white/25"
                >
                    <ChevronDown size={13} className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                </button>

            </div>

            {/* Dropdown Menu */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 5, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 5, scale: 0.98 }}
                        transition={{ duration: 0.15, ease: "easeOut" }}
                        className="absolute top-9 right-0 w-64 bg-[hsl(var(--bg-primary))] dark:bg-[#252628] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-[0_10px_40px_-10px_rgba(0,0,0,0.2)] py-2 z-[100] origin-top-right overflow-hidden"
                    >
                        <div className="px-3 pb-2 pt-1 mb-1 flex items-center justify-between border-b border-[hsl(var(--border))] dark:border-white/5">
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Crear</span>
                            <span className="text-[10px] font-bold text-[hsl(var(--primary))] cursor-pointer hover:underline">Gestionar</span>
                        </div>

                        <div className="px-1.5 flex flex-col gap-0.5">
                            {displayOptions.map((opt, idx) => (
                                <DropdownItem 
                                    key={opt.id} 
                                    icon={opt.icon} 
                                    label={opt.label} 
                                    onClick={() => handleOption(opt.id, opt.onClick)} 
                                    selected={idx === 0} 
                                />
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function DropdownItem({ icon: Icon, label, selected, onClick }: any) {
    return (
        <button 
            onClick={onClick}
            className={`w-full flex items-center gap-3 px-3 py-1.5 rounded-lg text-[13px] text-left transition-all ${
                selected 
                    ? 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white font-bold' 
                    : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5'
            }`}
        >
            {selected && <div className="absolute left-1.5 size-1.5 rounded-full bg-[hsl(var(--primary))]" />}
            {Icon && <Icon size={14} className={selected ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))]'} />}
            {!Icon && <span className="w-3" />}
            <span>{label}</span>
        </button>
    );
}
