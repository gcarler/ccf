"use client";

import React from "react";
import { CalendarDays, Construction, GanttChartSquare, Sparkles } from "lucide-react";
import { ViewType } from "@/components/ViewSwitcher";
import UniversalGanttView from "@/components/ui/UniversalGanttView";
import UniversalCalendarView from "@/components/ui/UniversalCalendarView";
import UniversalWikiView from "@/components/ui/UniversalWikiView";

const VIEW_LABEL: Record<ViewType, string> = {
  dashboard: "Resumen",
  table: "Tabla",
  list: "Lista",
  grid: "Grid",
  board: "Tablero",
  kanban: "Kanban",
  gantt: "Gantt",
  calendar: "Calendario",
  wiki: "Wiki",
};

type CalendarEvents = React.ComponentProps<typeof UniversalCalendarView>["events"];
type GanttItems = React.ComponentProps<typeof UniversalGanttView>["items"];

export default function CrmViewPlaceholder({
  moduleName,
  viewType,
  calendarEvents,
  ganttItems,
}: {
  moduleName: string;
  viewType: ViewType;
  calendarEvents?: CalendarEvents;
  ganttItems?: GanttItems;
}) {
  if (viewType === "gantt") {
    if (ganttItems?.length) {
      return <UniversalGanttView items={ganttItems} moduleName={moduleName} />;
    }
    return (
      <EmptyOperationalView
        icon={GanttChartSquare}
        title={`Sin timeline para ${moduleName}`}
        description="Esta vista no tiene suficientes datos fechados para construir un gantt real."
      />
    );
  }

  if (viewType === "calendar") {
    if (calendarEvents?.length) {
      return <UniversalCalendarView events={calendarEvents} title={`Calendario: ${moduleName}`} />;
    }
    return (
      <EmptyOperationalView
        icon={CalendarDays}
        title={`Sin calendario para ${moduleName}`}
        description="Esta vista no tiene eventos con fecha para mostrar. No se insertan ejemplos ni datos simulados."
      />
    );
  }

  if (viewType === "wiki") {
    return <UniversalWikiView moduleName={moduleName} storageKey={`wiki_${moduleName.toLowerCase()}`} />;
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 text-center shadow-sm">
      <div className="mx-auto mb-3 flex size-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400">
        <Construction size={32} />
      </div>
      <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 uppercase italic tracking-tighter">
        Vista {VIEW_LABEL[viewType]} pendiente de datos
      </h3>
      <p className="mt-3 text-sm font-medium text-slate-500 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
        {moduleName}: esta perspectiva aun no tiene una implementacion de datos reales conectada. Usa las vistas operativas disponibles.
      </p>
      <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-slate-100 dark:bg-white/10 px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-500 dark:text-slate-300">
        <Sparkles size={12} className="text-indigo-500" /> Sin datos simulados
      </div>
    </div>
  );
}

function EmptyOperationalView({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 text-center shadow-sm">
      <div className="mx-auto mb-3 flex size-8 items-center justify-center rounded-lg bg-slate-50 text-slate-500 dark:bg-white/5 dark:text-slate-300">
        <Icon size={32} />
      </div>
      <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 uppercase italic tracking-tighter">
        {title}
      </h3>
      <p className="mt-3 text-sm font-medium text-slate-500 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
        {description}
      </p>
    </div>
  );
}
