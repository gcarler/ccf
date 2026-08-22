'use client';

import { CheckCircle2, Loader2, Users } from 'lucide-react';
import React from 'react';
import type { AttendanceData } from '../useGroupDetailPage';

interface GroupAttendeeListProps {
  loadingAtt: boolean;
  attendance: AttendanceData | null;
}

export function GroupAttendeeList({ loadingAtt, attendance }: GroupAttendeeListProps) {
  if (loadingAtt) {
    return (
      <div className="flex items-center justify-center py-1.5">
        <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={24} />
      </div>
    );
  }
  if (!attendance || attendance.attendees.length === 0) {
    return (
      <div className="py-1.5 text-center bg-[hsl(var(--bg-muted))] rounded-lg text-[hsl(var(--text-secondary))]">
        <Users size={32} className="mx-auto mb-3 opacity-30" />
        <p className="font-bold text-sm">Sin asistentes registrados</p>
        <p className="text-xs mt-1">Usa el botón &ldquo;Añadir Asistentes&rdquo; para marcar presentes</p>
      </div>
    );
  }
  return (
    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[var(--admin-bg-secondary)] rounded-md border border-[hsl(var(--border-primary))] overflow-hidden shadow-sm">
      <div className="px-4 py-2 border-b border-[hsl(var(--border-primary))] flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
          <CheckCircle2 size={14} className="text-[hsl(var(--success))]" /> Lista de Asistencia
        </h3>
        <span className="text-xs font-semibold text-[hsl(var(--primary))] bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info))]/30 px-3 py-1 rounded-lg">{attendance.total} personas</span>
      </div>
      <div className="divide-y divide-[hsl(var(--border-primary))]">
        {attendance.attendees.map((a) => (
          <div key={a.persona_id} className="flex items-center gap-4 px-4 py-1.5 hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 transition-colors">
            <div className="size-8 rounded-md bg-gradient-to-br from-[hsl(var(--info))] to-[hsl(var(--info))] text-white flex items-center justify-center text-xs font-semibold shrink-0">
              {a.name.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{a.name}</p>
              {a.role && <p className="text-2xs text-[hsl(var(--text-secondary))] font-medium">{a.role}</p>}
            </div>
            <CheckCircle2 size={16} className="text-[hsl(var(--success))] shrink-0" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default GroupAttendeeList;
