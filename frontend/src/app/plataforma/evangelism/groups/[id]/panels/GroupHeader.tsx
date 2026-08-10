'use client';

import { Activity, Clock, MapPin, Users } from 'lucide-react';
import { ArrowLeft } from 'lucide-react';
import React from 'react';
import type { HouseDetail } from '../useGroupDetailPage';

interface GroupHeaderProps {
  house: HouseDetail;
  avgAttendance: number;
  onBack: () => void;
}

export function GroupHeader({ house, avgAttendance, onBack }: GroupHeaderProps) {
  return (
    <>
      <button onClick={onBack} className="flex items-center gap-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-primary))] transition-colors mb-4 text-xs font-bold uppercase tracking-wide">
        <ArrowLeft size={14} /> Volver
      </button>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Grupos en Casa</p>
          <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] tracking-tight">{house.name}</h1>
          <div className="flex flex-wrap gap-4 text-xs text-[hsl(var(--text-secondary))] font-medium mt-1.5">
            {house.code && <span className="flex items-center gap-1.5"><Activity size={12} /> Código: {house.code}</span>}
            {house.leader_name && <span className="flex items-center gap-1.5"><Users size={12} /> Líder: {house.leader_name}</span>}
            {house.address && <span className="flex items-center gap-1.5"><MapPin size={12} /> {house.address}</span>}
            {house.day_of_week && <span className="flex items-center gap-1.5"><Clock size={12} /> {house.day_of_week} {house.time || ''}</span>}
          </div>
        </div>
        <div className="flex gap-3 shrink-0">
          <div className="text-center px-3 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-md border border-[hsl(var(--border-primary))] shadow-sm">
            <p className="text-base font-bold text-[hsl(var(--text-primary))]">{house.total_sessions}</p>
            <p className="text-2xs text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide mt-0.5">Sesiones</p>
          </div>
          <div className="text-center px-3 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-md border border-[hsl(var(--border-primary))] shadow-sm">
            <p className="text-base font-bold text-[hsl(var(--text-primary))]">{house.total_attendance}</p>
            <p className="text-2xs text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide mt-0.5">Asistentes</p>
          </div>
          <div className="text-center px-3 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-md border border-[hsl(var(--border-primary))] shadow-sm">
            <p className="text-base font-bold text-[hsl(var(--text-primary))]">{avgAttendance}</p>
            <p className="text-2xs text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide mt-0.5">Promedio</p>
          </div>
        </div>
      </div>
    </>
  );
}

export default GroupHeader;
