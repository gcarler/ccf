"use client";

import React from "react";
import { BookOpen, Construction, Sparkles } from "lucide-react";
import { ViewType } from "@/components/ViewSwitcher";
import UniversalGanttView from "@/components/ui/UniversalGanttView";
import UniversalCalendarView from "@/components/ui/UniversalCalendarView";
import UniversalWikiView from "@/components/ui/UniversalWikiView";

const VIEW_LABEL: Record<ViewType, string> = {
  table: "Tabla",
  list: "Lista",
  grid: "Grid",
  board: "Tablero",
  kanban: "Kanban",
  gantt: "Gantt",
  calendar: "Calendario",
  wiki: "Wiki",
};

// ── Mock Data Generators for Placeholders ──

const MOCK_GANTT_ITEMS = [
    { id: 1, title: 'Fase Inicial de Crecimiento', subtitle: 'Liderazgo', start_date: '2024-04-10', end_date: '2024-04-15', color: 'blue' as const, progress: 65 },
    { id: 2, title: 'Consolidación de Miembros', subtitle: 'Pastoral', start_date: '2024-04-12', end_date: '2024-04-20', color: 'purple' as const, progress: 30 },
    { id: 3, title: 'Evento Regional Ebenezer', subtitle: 'Redes', start_date: '2024-04-14', end_date: '2024-04-14', color: 'amber' as const, progress: 0 },
    { id: 4, title: 'Auditoría de Procesos', subtitle: 'Admin', start_date: '2024-04-16', end_date: '2024-04-18', color: 'rose' as const },
];

const MOCK_CALENDAR_EVENTS = [
    { id: 1, title: 'Servicio Dominical', date: '2024-04-14', color: 'blue' as const, location: 'Auditorio Central' },
    { id: 2, title: 'Reunión de Líderes', date: '2024-04-16', color: 'purple' as const },
    { id: 3, title: 'Bautismos', date: '2024-04-21', color: 'emerald' as const },
];

export default function CrmViewPlaceholder({
  moduleName,
  viewType,
}: {
  moduleName: string;
  viewType: ViewType;
}) {
  
  // Render real components if available
  if (viewType === 'gantt') {
      return <UniversalGanttView items={MOCK_GANTT_ITEMS} moduleName={moduleName} />;
  }

  if (viewType === 'calendar') {
      return <UniversalCalendarView events={MOCK_CALENDAR_EVENTS} title={`Calendario: ${moduleName}`} />;
  }

  if (viewType === 'wiki') {
      return <UniversalWikiView moduleName={moduleName} storageKey={`wiki_${moduleName.toLowerCase()}`} />;
  }

  // Fallback for types not yet "Universalized" (Kanban/Board often implemented inline)
  return (
    <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-16 text-center shadow-sm">
      <div className="mx-auto mb-6 flex size-16 items-center justify-center rounded-[1.5rem] bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400">
        <Construction size={32} />
      </div>
      <h3 className="text-xl font-black text-slate-900 dark:text-slate-100 uppercase italic tracking-tighter">
        Vista {VIEW_LABEL[viewType]} en optimización
      </h3>
      <p className="mt-3 text-sm font-medium text-slate-500 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
        {moduleName}: Estamos calibrando los motores de visualización para esta perspectiva. Usa las vistas de Grid o Tabla para operación inmediata.
      </p>
      <div className="mt-8 inline-flex items-center gap-2 rounded-full bg-slate-100 dark:bg-white/10 px-4 py-1.5 text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-300">
        <Sparkles size={12} className="text-indigo-500" /> Clean Productivity 3.0
      </div>
    </div>
  );
}
