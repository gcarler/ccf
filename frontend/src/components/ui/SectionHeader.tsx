import { LucideIcon } from 'lucide-react';
import clsx from 'clsx';
import React from 'react';

interface SectionHeaderProps {
    label: string;
    icon?: LucideIcon;
    caption?: string;
    actions?: React.ReactNode;
    className?: string;
}

export function SectionHeader({ label, icon: Icon, caption, actions, className }: SectionHeaderProps) {
    return (
        <div className={clsx('flex items-center justify-between gap-3 flex-wrap', className)}>
            <div className="flex items-center gap-2">
                {Icon && (
                    <div className="w-6 h-6 rounded-md bg-slate-900/5 dark:bg-white/10 flex items-center justify-center text-slate-500 dark:text-slate-300">
                        <Icon size={13} />
                    </div>
                )}
                <div>
                    <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">{label}</p>
                    {caption && <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">{caption}</span>}
                </div>
            </div>
            {actions && <div className="flex items-center gap-1.5">{actions}</div>}
        </div>
    );
}

export default SectionHeader;
