import React from 'react';
import * as Popover from '@radix-ui/react-popover';
import { Clock, Users, AlignLeft } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

interface InlineEventPopoverProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    day: Date;
    children: React.ReactNode;
}

export default function InlineEventPopover({ open, onOpenChange, day, children }: InlineEventPopoverProps) {
    return (
        <Popover.Root open={open} onOpenChange={onOpenChange}>
            <Popover.Trigger asChild>
                {children}
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content 
                    side="right" 
                    align="start" 
                    sideOffset={8}
                    className="z-[100] w-[340px] bg-white dark:bg-[#25262b] rounded-2xl shadow-2xl shadow-black/10 dark:shadow-black/40 border border-slate-100 dark:border-white/10 p-5 font-display flex flex-col gap-4 animate-in fade-in zoom-in-95 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="flex flex-col gap-1">
                        <input 
                            autoFocus
                            type="text" 
                            placeholder="Añade un título..." 
                            className="w-full text-[18px] font-medium bg-transparent border-none outline-none placeholder:text-slate-400 text-slate-800 dark:text-white mb-2"
                        />
                        <div className="flex gap-2 text-[11px] font-black uppercase tracking-widest">
                            <button className="flex-1 py-1.5 bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400 rounded-lg border border-blue-100 dark:border-blue-500/20">Evento</button>
                            <button className="flex-1 py-1.5 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 rounded-lg transition-colors">Tarea</button>
                        </div>
                    </div>

                    <div className="flex flex-col gap-3">
                        <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300">
                            <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center shrink-0">
                                <Clock size={14} className="text-slate-400" />
                            </div>
                            <div className="flex flex-col text-[12px]">
                                <span className="font-semibold">{format(day, 'EEEE, d MMMM', { locale: es })}</span>
                                <span className="text-slate-400 text-[11px]">Todo el día • Seleccionar hora</span>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300">
                            <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center shrink-0">
                                <Users size={14} className="text-slate-400" />
                            </div>
                            <input type="text" placeholder="Añadir invitados" className="text-[12px] bg-transparent outline-none w-full placeholder:text-slate-400" />
                        </div>

                        <div className="flex items-start gap-3 text-slate-600 dark:text-slate-300">
                            <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center shrink-0 mt-1">
                                <AlignLeft size={14} className="text-slate-400" />
                            </div>
                            <textarea 
                                rows={2} 
                                placeholder="Añadir descripción..." 
                                className="text-[12px] bg-transparent outline-none w-full placeholder:text-slate-400 py-2 resize-none" 
                            />
                        </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-white/10">
                        <button 
                            onClick={() => onOpenChange(false)}
                            className="px-4 py-2 text-[11px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 rounded-xl transition-colors"
                        >
                            Cerrar
                        </button>
                        <button 
                            onClick={() => onOpenChange(false)}
                            className="px-4 py-2 text-[11px] font-black uppercase tracking-widest bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20 rounded-xl transition-all active:scale-95"
                        >
                            Guardar
                        </button>
                    </div>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}
