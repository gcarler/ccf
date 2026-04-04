"use client";

import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Plus, FileText, Bell, LayoutDashboard, Layout } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface SplitDropdownButtonProps {
    onMainClick: () => void;
    onOptionClick: (type: 'task' | 'document' | 'reminder' | 'whiteboard' | 'panel') => void;
}

export default function SplitDropdownButton({ onMainClick, onOptionClick }: SplitDropdownButtonProps) {
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

    const handleOption = (type: 'task' | 'document' | 'reminder' | 'whiteboard' | 'panel') => {
        setIsOpen(false);
        onOptionClick(type);
    };

    return (
        <div className="relative inline-flex items-center ml-2" ref={dropdownRef}>
            {/* Split Button Container */}
            <div className="flex items-center bg-[#1e272e] hover:bg-[#2f3640] text-white rounded-[7px] overflow-hidden transition-all shadow-sm">
                
                {/* Main Action (Añadir Tarea) */}
                <button 
                    onClick={onMainClick}
                    className="h-9 px-3.5 text-[11px] font-bold flex items-center gap-1.5 transition-colors border-r border-white/10 active:bg-white/10 whitespace-nowrap"
                >
                    Añadir Tarea
                </button>

                {/* Dropdown Chevron */}
                <button 
                    onClick={() => setIsOpen(!isOpen)}
                    className="h-9 w-9 flex items-center justify-center transition-colors hover:bg-white/10 active:bg-white/20"
                >
                    <ChevronDown size={14} className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
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
                        className="absolute top-9 right-0 w-64 bg-white dark:bg-[#252628] border border-slate-200 dark:border-white/10 rounded-xl shadow-[0_10px_40px_-10px_rgba(0,0,0,0.2)] py-2 z-[100] origin-top-right overflow-hidden"
                    >
                        <div className="px-3 pb-2 pt-1 mb-1 flex items-center justify-between border-b border-slate-100 dark:border-white/5">
                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Crear</span>
                            <span className="text-[10px] font-bold text-blue-500 cursor-pointer hover:underline">Gestionar</span>
                        </div>

                        <div className="px-1.5 flex flex-col gap-0.5">
                            <DropdownItem icon={Plus} label="Tarea" onClick={() => handleOption('task')} selected />
                            <DropdownItem icon={FileText} label="Documento" onClick={() => handleOption('document')} />
                            <DropdownItem icon={Bell} label="Recordatorio" onClick={() => handleOption('reminder')} />
                            <DropdownItem icon={LayoutDashboard} label="Pizarra" onClick={() => handleOption('whiteboard')} />
                            <DropdownItem icon={Layout} label="Panel" onClick={() => handleOption('panel')} />
                        </div>

                        <div className="h-[1px] bg-slate-100 dark:bg-white/5 my-1.5" />
                        
                        <div className="px-1.5 flex flex-col gap-0.5">
                            <DropdownItem label="Crear tipo de tarea" />
                            <DropdownItem label="Tarea de otra lista" />
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
                    ? 'bg-slate-50 dark:bg-white/5 text-slate-900 dark:text-white font-bold' 
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5'
            }`}
        >
            {selected && <div className="absolute left-1.5 size-1.5 rounded-full bg-blue-500" />}
            {Icon && <Icon size={14} className={selected ? 'text-blue-500' : 'text-slate-400'} />}
            {!Icon && <span className="w-3" />}
            <span>{label}</span>
        </button>
    );
}
