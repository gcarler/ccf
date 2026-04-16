import { UserPlus, Phone, Calendar, Sparkles, CheckCircle2 } from 'lucide-react';
import { StatusOption } from '@/components/ui/StatusPicker';

export const PIPELINE_STAGES: (StatusOption & { dot: string; colBg: string; emptyIcon: any })[] = [
    { label: 'NUEVO', value: 'new', color: 'bg-blue-500', dot: 'bg-blue-500', text: 'text-blue-600', bg: 'bg-blue-50', colBg: 'bg-blue-500/5', emptyIcon: UserPlus },
    { label: 'POR LLAMAR', value: 'call', color: 'bg-amber-500', dot: 'bg-amber-500', text: 'text-amber-600', bg: 'bg-amber-50', colBg: 'bg-amber-500/5', emptyIcon: Phone },
    { label: 'VISITA', value: 'visit', color: 'bg-purple-500', dot: 'bg-purple-500', text: 'text-purple-600', bg: 'bg-purple-50', colBg: 'bg-purple-500/5', emptyIcon: Calendar },
    { label: 'DISCIPULADO', value: 'discipleship', color: 'bg-indigo-500', dot: 'bg-indigo-500', text: 'text-indigo-600', bg: 'bg-indigo-50', colBg: 'bg-indigo-500/5', emptyIcon: Sparkles },
    { label: 'CONSOLIDADO', value: 'consolidated', color: 'bg-emerald-500', dot: 'bg-emerald-500', text: 'text-emerald-600', bg: 'bg-emerald-50', colBg: 'bg-emerald-500/5', emptyIcon: CheckCircle2 },
];

export const STAGE_LABEL: Record<string, string> = {
    new: 'Nuevo', call: 'Por Llamar', visit: 'Visita',
    discipleship: 'Discipulado', consolidated: 'Consolidado',
    contacted: 'Contactado', in_process: 'En Proceso', lost: 'Perdido',
};

export const SOURCES: Record<string, string> = {
    Visitante: '🧑‍🤝‍🧑', Referido: '🤝', Web: '🌐',
    'Redes Sociales': '📱', Evento: '🎯', Otro: '📌',
};

export const STAGE_PROGRESS: Record<string, number> = { 
    new: 20, call: 40, visit: 60, discipleship: 80, consolidated: 100 
};
