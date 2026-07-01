"use client";

import React from "react";
import {CalendarDays, Construction, GanttChartSquare, Sparkles} from "lucide-react";
import { ViewType } from "@/components/ViewSwitcher";
import UniversalGanttView from "@/components/ui/UniversalGanttView";
import UniversalCalendarView from "@/components/ui/UniversalCalendarView";
import UniversalWikiView from "@/components/ui/UniversalWikiView";
import UniversalListView from "@/components/ui/UniversalListView";

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
  chat: "Chat",
};

type CalendarEvents = React.ComponentProps<typeof UniversalCalendarView>["events"];
type GanttItems = React.ComponentProps<typeof UniversalGanttView>["items"];
type ListItems = React.ComponentProps<typeof UniversalListView>["items"];

export default function CrmViewPlaceholder({
  moduleName,
  viewType,
  calendarEvents,
  ganttItems,
  listItems,
}: {
  moduleName: string;
  viewType: ViewType;
  calendarEvents?: CalendarEvents;
  ganttItems?: GanttItems;
  listItems?: ListItems;
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

    if (viewType === "list") {
      return (
      <UniversalListView
        items={listItems || []}
        title={`${moduleName} — Lista`}
        emptyMessage={`No hay elementos en la lista de ${moduleName}`}
      />
    );
  }

  if (viewType === "wiki") {
    return <UniversalWikiView moduleName={moduleName} storageKey={`wiki_${moduleName.toLowerCase()}`} />;
  }

  return (
    <div className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 p-4 text-center shadow-sm">
      <div className="mx-auto mb-3 flex size-8 items-center justify-center rounded-lg bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-900/20 dark:text-[hsl(var(--primary))]">
        <Construction size={32} />
      </div>
      <h3 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] uppercase italic tracking-tighter">
        Vista {VIEW_LABEL[viewType]} pendiente de datos
      </h3>
      <p className="mt-3 text-sm font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] max-w-sm mx-auto leading-relaxed">
        {moduleName}: esta perspectiva aun no tiene una implementacion de datos reales conectada. Usa las vistas operativas disponibles.
      </p>
      <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10 px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
        <Sparkles size={12} className="text-[hsl(var(--primary))]" /> Sin datos simulados
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
    <div className="rounded-md border border-dashed border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 p-4 text-center shadow-sm">
      <div className="mx-auto mb-3 flex size-8 items-center justify-center rounded-lg bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]">
        <Icon size={32} />
      </div>
      <h3 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] uppercase italic tracking-tighter">
        {title}
      </h3>
      <p className="mt-3 text-sm font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] max-w-sm mx-auto leading-relaxed">
        {description}
      </p>
    </div>
  );
}
