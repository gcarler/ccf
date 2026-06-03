import React, { useState } from 'react';
import * as Popover from '@radix-ui/react-popover';
import { Clock, Users, AlignLeft, Loader2 } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

interface InlineEventPopoverProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    day: Date;
    children: React.ReactNode;
    onSave?: (data: { title: string; type: 'event'|'task'; description: string; location: string; date: Date }) => Promise<void> | void;
}

export default function InlineEventPopover({ open, onOpenChange, day, children, onSave }: InlineEventPopoverProps) {
    const [title, setTitle] = useState('');
    const [type, setType] = useState<'event'|'task'>('event');
    const [location, setLocation] = useState('');
    const [description, setDescription] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // Reset when opened
    React.useEffect(() => {
        if (open) {
            setTitle('');
            setType('event');
            setLocation('');
            setDescription('');
            setIsSaving(false);
        }
    }, [open]);

    const handleSave = async () => {
        if (!title.trim()) return; // Validación básica
        setIsSaving(true);
        try {
            if (onSave) {
                await onSave({ title: title.trim(), type, description: description.trim(), location: location.trim(), date: day });
            }
            onOpenChange(false);
        } finally {
            setIsSaving(false);
        }
    };

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
                    collisionPadding={16}
                    className="z-[100] w-[340px] bg-[hsl(var(--bg-primary))] dark:bg-[#25262b] rounded-lg shadow-2xl shadow-black/10 dark:shadow-black/40 border border-slate-100 dark:border-white/10 p-3 font-display flex flex-col gap-4 animate-in fade-in zoom-in-95 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="flex flex-col gap-1">
                        <input 
                            autoFocus
                            type="text" 
                            placeholder="Añade un título..." 
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                            className="w-full text-base font-medium bg-transparent border-none outline-none placeholder:text-slate-400 text-slate-800 dark:text-white mb-2"
                        />
                        <div className="flex gap-2 text-[11px] font-semibold uppercase tracking-wide">
                            <button 
                                onClick={() => setType('event')}
                                className={`flex-1 py-1.5 rounded-lg border transition-colors ${type === 'event' ? 'bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-[hsl(var(--primary))] border-blue-100 dark:border-blue-500/20' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 border-transparent'}`}
                            >
                                Evento
                            </button>
                            <button 
                                onClick={() => setType('task')}
                                className={`flex-1 py-1.5 rounded-lg border transition-colors ${type === 'task' ? 'bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-[hsl(var(--primary))] border-blue-100 dark:border-blue-500/20' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 border-transparent'}`}
                            >
                                Tarea
                            </button>
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
                            <input 
                                type="text" 
                                placeholder="Añadir invitados" 
                                value={location}
                                onChange={(e) => setLocation(e.target.value)}
                                className="text-[12px] bg-transparent outline-none w-full placeholder:text-slate-400" 
                            />
                        </div>

                        <div className="flex items-start gap-3 text-slate-600 dark:text-slate-300">
                            <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center shrink-0 mt-1">
                                <AlignLeft size={14} className="text-slate-400" />
                            </div>
                            <textarea 
                                rows={2} 
                                placeholder="Añadir descripción..." 
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                className="text-[12px] bg-transparent outline-none w-full placeholder:text-slate-400 py-2 resize-none scrollbar-thin" 
                            />
                        </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-white/10">
                        <button 
                            onClick={() => onOpenChange(false)}
                            className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 rounded-md transition-colors disabled:opacity-50"
                            disabled={isSaving}
                        >
                            Cerrar
                        </button>
                        <button 
                            onClick={handleSave}
                            disabled={!title.trim() || isSaving}
                            className="flex items-center gap-2 px-4 py-2 text-[11px] font-semibold uppercase tracking-wide bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white shadow-md shadow-blue-500/20 rounded-md transition-all active:scale-95 disabled:opacity-50 disabled:active:scale-100"
                        >
                            {isSaving && <Loader2 size={12} className="animate-spin" />}
                            Guardar
                        </button>
                    </div>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}
