import type { ReactNode } from 'react';

export default function MetaRow({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
    return (
        <div className="flex items-center gap-0">
            <div className="w-[140px] shrink-0 flex items-center gap-2 text-[11px] font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                {icon}
                {label}
            </div>
            {children}
        </div>
    );
}
