import { UserPlus, Phone, Calendar, Sparkles, CheckCircle2 } from 'lucide-react';
import { StatusOption } from '@/components/ui/StatusPicker';

export const PIPELINE_STAGES: (StatusOption & { dot: string; colBg: string; emptyIcon: any })[] = [
    { label: 'NUEVO', value: 'new', color: 'bg-[hsl(var(--primary))]', dot: 'bg-[hsl(var(--primary))]', text: 'text-[hsl(var(--primary))]', bg: 'bg-blue-50', colBg: 'bg-blue-500/5', emptyIcon: UserPlus },
    { label: 'POR LLAMAR', value: 'call', color: 'bg-amber-500', dot: 'bg-amber-500', text: 'text-amber-600', bg: 'bg-amber-50', colBg: 'bg-amber-500/5', emptyIcon: Phone },
    { label: 'VISITA', value: 'visit', color: 'bg-sky-500', dot: 'bg-sky-500', text: 'text-sky-600', bg: 'bg-sky-50', colBg: 'bg-sky-500/5', emptyIcon: Calendar },
    { label: 'DISCIPULADO', value: 'discipleship', color: 'bg-sky-500', dot: 'bg-sky-500', text: 'text-sky-600', bg: 'bg-sky-50', colBg: 'bg-sky-500/5', emptyIcon: Sparkles },
    { label: 'CONSOLIDADO', value: 'consolidated', color: 'bg-emerald-500', dot: 'bg-emerald-500', text: 'text-emerald-600', bg: 'bg-emerald-50', colBg: 'bg-emerald-500/5', emptyIcon: CheckCircle2 },
];

export const STAGE_LABEL: Record<string, string> = {
    new: 'Nuevo', call: 'Por Llamar', visit: 'Visita',
    discipleship: 'Discipulado', consolidated: 'Consolidado',
    contacted: 'Por Llamar', visited: 'Visita', in_process: 'Discipulado',
    integrated: 'Consolidado', converted: 'Consolidado', lost: 'Perdido',
};

export const SOURCES: Record<string, string> = {
    Visitante: '🧑‍🤝‍🧑', Referido: '🤝', Web: '🌐',
    'Redes Sociales': '📱', Evento: '🎯', Otro: '📌',
};

export const STAGE_PROGRESS: Record<string, number> = { 
    new: 20, call: 40, visit: 60, discipleship: 80, consolidated: 100,
    contacted: 40, visited: 60, in_process: 80, integrated: 100, converted: 100, lost: 0,
};
