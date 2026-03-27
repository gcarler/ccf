"use client";

import React from "react";
import clsx from "clsx";
import { LucideIcon, CornerDownLeft } from "lucide-react";

interface DSCommandEntryProps {
  label: string;
  description?: string;
  shortcut?: string;
  icon?: LucideIcon;
  active?: boolean;
}

export function DSCommandEntry({
  label,
  description,
  shortcut,
  icon: Icon,
  active = false,
}: DSCommandEntryProps) {
  return (
    <div
      className={clsx(
        "flex items-center gap-3 rounded-2xl border px-3 py-2.5 transition-all",
        active
          ? "border-blue-500/40 bg-blue-600 text-white shadow-lg shadow-blue-500/20"
          : "border-slate-200 bg-white text-slate-700 hover:border-blue-300 hover:bg-blue-50",
      )}
    >
      <div
        className={clsx(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl",
          active ? "bg-white/20 text-white" : "bg-slate-100 text-slate-500",
        )}
      >
        {Icon ? <Icon size={16} /> : <CornerDownLeft size={16} />}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-black tracking-tight">{label}</p>
        {description ? (
          <p className={clsx("truncate text-xs", active ? "text-white/80" : "text-slate-500")}>
            {description}
          </p>
        ) : null}
      </div>
      {shortcut ? (
        <span
          className={clsx(
            "rounded-lg px-2 py-1 text-[10px] font-black uppercase tracking-widest",
            active ? "bg-white/20 text-white" : "bg-slate-100 text-slate-400",
          )}
        >
          {shortcut}
        </span>
      ) : null}
    </div>
  );
}
