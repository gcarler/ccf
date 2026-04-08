"use client";

import React from "react";
import { BookOpen, Construction, Sparkles } from "lucide-react";
import { ViewType } from "@/components/ViewSwitcher";

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

export default function CrmViewPlaceholder({
  moduleName,
  viewType,
}: {
  moduleName: string;
  viewType: ViewType;
}) {
  return (
    <div className="rounded-[2rem] border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-10 text-center">
      <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400">
        {viewType === "wiki" ? <BookOpen size={20} /> : <Construction size={20} />}
      </div>
      <h3 className="text-[15px] font-bold text-slate-900 dark:text-slate-100">
        Vista {VIEW_LABEL[viewType]} en construccion
      </h3>
      <p className="mt-2 text-[12px] font-medium text-slate-500 dark:text-slate-400">
        {moduleName}: esta vista aun no esta implementada. Usa otra vista para operar mientras se completa.
      </p>
      <div className="mt-4 inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-slate-500 dark:bg-white/10 dark:text-slate-300">
        <Sparkles size={11} /> Clean Productivity
      </div>
    </div>
  );
}
