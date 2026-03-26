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
        <div className={clsx('flex items-center justify-between px-2 gap-4 flex-wrap', className)}>
            <div className="flex items-center gap-3">
                {Icon && (
                    <div className="w-8 h-8 rounded-xl bg-slate-900/5 dark:bg-white/10 flex items-center justify-center text-slate-500 dark:text-slate-300">
                        <Icon size={16} />
                    </div>
                )}
                <div>
                    <p className="text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.28em]">{label}</p>
                    {caption && <span className="text-[12px] text-slate-500 dark:text-slate-400 font-medium">{caption}</span>}
                </div>
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
    );
}

export default SectionHeader;
