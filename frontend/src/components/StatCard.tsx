import React from 'react';
import { LucideIcon, ArrowUpRight } from 'lucide-react';

interface StatCardProps {
    label: string;
    value: string | number;
    icon: LucideIcon;
    color: string;
    bg: string;
    desc?: string;
    trend?: string;
}

export const StatCard: React.FC<StatCardProps> = ({ 
    label, value, icon: Icon, color, bg, desc, trend 
}) => (
    <div className="group relative bg-[#1e1f21] border border-white/5 p-3 rounded-lg hover:border-primary/50 transition-all duration-500 overflow-hidden">
        <div className={`absolute top-0 right-0 p-4 opacity-5 group-hover:scale-150 transition-transform duration-700 ${color}`}>
            <Icon size={80} />
        </div>
        <div className="space-y-4 relative z-10">
            <div className={`w-12 h-8 ${bg} rounded-md flex items-center justify-center ${color} group-hover:rotate-12 transition-transform`}>
                <Icon size={24} />
            </div>
            <div>
                <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wide mb-1">{label}</div>
                <div className="text-xl font-black text-white tabular-nums tracking-tighter italic">
                    {value}
                </div>
            </div>
            {(desc || trend) && (
                <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground leading-relaxed">{desc}</span>
                    {trend && (
                        <div className="flex items-center gap-1 font-semibold text-primary">
                            {trend} <ArrowUpRight size={12} />
                        </div>
                    )}
                </div>
            )}
        </div>
    </div>
);
