import clsx from 'clsx';
import { LucideIcon } from 'lucide-react';

type MetricTone = 'blue' | 'indigo' | 'emerald' | 'amber' | 'pink' | 'slate';

const COLOR_STYLES: Record<MetricTone, string> = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300 border-blue-100 dark:border-blue-800',
    indigo: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-300 border-indigo-100 dark:border-indigo-800',
    emerald: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300 border-emerald-100 dark:border-emerald-800',
    amber: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-300 border-amber-100 dark:border-amber-800',
    pink: 'bg-pink-50 dark:bg-pink-900/20 text-pink-600 dark:text-pink-300 border-pink-100 dark:border-pink-900/40',
    slate: 'bg-slate-50 dark:bg-slate-900/20 text-slate-600 dark:text-slate-300 border-slate-100 dark:border-slate-800'
};

export interface MetricCardProps {
    title: string;
    value?: string | number;
    trend?: string;
    icon: LucideIcon;
    tone?: MetricTone;
    loading?: boolean;
    helper?: string;
}

export function MetricCard({
    title,
    value,
    trend,
    helper,
    icon: Icon,
    tone = 'blue',
    loading
}: MetricCardProps) {
    return (
        <article className="bg-[hsl(var(--surface-2))] p-6 rounded-[1.75rem] border border-[hsl(var(--border))] shadow-sm flex flex-col gap-3 hover:shadow-md transition-all">
            <div className="flex items-center justify-between">
                <div className={clsx('p-3 rounded-xl transition-transform group-hover:scale-105 shadow-sm', COLOR_STYLES[tone])}>
                    <Icon size={18} />
                </div>
                {trend && !loading && (
                    <span className={clsx('text-[10px] font-black px-2 py-0.5 rounded-full uppercase tracking-widest', COLOR_STYLES[tone])}>{trend}</span>
                )}
            </div>
            <div>
                <p className="text-[10px] font-black text-[hsl(var(--text-secondary))] uppercase tracking-[0.2em] mb-1">{title}</p>
                {loading ? (
                    <div className="h-6 w-1/2 bg-[hsl(var(--border))] rounded-full animate-pulse" />
                ) : (
                    <span className="text-3xl font-black text-[hsl(var(--text-primary))]">{value}</span>
                )}
            </div>
            {helper && (
                <p className="text-[11px] text-slate-500 dark:text-[hsl(var(--text-secondary))]">{helper}</p>
            )}
        </article>
    );
}

export default MetricCard;

