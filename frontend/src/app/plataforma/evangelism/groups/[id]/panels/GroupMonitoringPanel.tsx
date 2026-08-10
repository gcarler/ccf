'use client';

import { Activity, BarChart3, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import React from 'react';
import {
  ATTENDANCE_REASON_OPTIONS,
  type AttendanceReason,
  type AttendeeRow,
  type HouseMonitoring,
  type MonitoringAlert,
  type MonitoringTrendRow,
  type RepeatAbsentee,
  type SessionRow,
} from '../useGroupDetailPage';

interface GroupMonitoringPanelProps {
  houseMonitoring?: HouseMonitoring;
  avgAttendance: number;
  activeSession: SessionRow | null;
  activeSessionEnabled: boolean;
  reportTopic: string;
  setReportTopic: (v: string) => void;
  reportOfferingAmount: string;
  setReportOfferingAmount: (v: string) => void;
  reportStatus: 'Realizada' | 'Cancelada' | 'No realizada';
  setReportStatus: (v: 'Realizada' | 'Cancelada' | 'No realizada') => void;
  reportNoveltyType: string;
  setReportNoveltyType: (v: string) => void;
  reportNoveltyDetail: string;
  setReportNoveltyDetail: (v: string) => void;
  reportCancellationReason: string;
  setReportCancellationReason: (v: string) => void;
  reportNotes: string;
  setReportNotes: (v: string) => void;
  reportPersonas: AttendeeRow[];
  setReportPersonas: React.Dispatch<React.SetStateAction<AttendeeRow[]>>;
  savingReport: boolean;
  onSaveReport: () => void;
}

export function GroupMonitoringPanel({
  houseMonitoring,
  avgAttendance,
  activeSession,
  activeSessionEnabled,
  reportTopic,
  setReportTopic,
  reportOfferingAmount,
  setReportOfferingAmount,
  reportStatus,
  setReportStatus,
  reportNoveltyType,
  setReportNoveltyType,
  reportNoveltyDetail,
  setReportNoveltyDetail,
  reportCancellationReason,
  setReportCancellationReason,
  reportNotes,
  setReportNotes,
  reportPersonas,
  setReportPersonas,
  savingReport,
  onSaveReport,
}: GroupMonitoringPanelProps) {
  const trendRows: MonitoringTrendRow[] = houseMonitoring?.attendance_trend ?? [];
  const alerts: MonitoringAlert[] = houseMonitoring?.alerts ?? [];
  const repeatAbsentees: RepeatAbsentee[] = houseMonitoring?.repeat_absentees ?? [];

  return (
    <div className="bg-[hsl(var(--bg-primary))] rounded-md border border-[hsl(var(--border-primary))] p-4 shadow-sm space-y-2">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] flex items-center gap-2">
          <BarChart3 className="text-[hsl(var(--primary))]" size={18} /> Monitoreo de la casa
        </h3>
        <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
          {houseMonitoring?.expected_personas ?? 0} esperados
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4 bg-[hsl(var(--bg-muted))] dark:bg-black/20">
          <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Promedio de presencia</p>
          <p className="mt-2 text-lg font-bold text-[hsl(var(--text-primary))]">{houseMonitoring?.average_attendance ?? avgAttendance}</p>
        </div>
        <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4 bg-[hsl(var(--bg-muted))] dark:bg-black/20">
          <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tasa promedio</p>
          <p className="mt-2 text-lg font-bold text-[hsl(var(--text-primary))]">{houseMonitoring?.average_attendance_rate ?? 0}%</p>
        </div>
        <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4 bg-[hsl(var(--bg-muted))] dark:bg-black/20">
          <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Alertas activas</p>
          <p className="mt-2 text-lg font-bold text-[hsl(var(--text-primary))]">{alerts.length}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tendencia reciente</p>
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{trendRows.length} sesiones</p>
          </div>
          <div className="space-y-3">
            {trendRows.length === 0 ? (
              <p className="text-sm text-[hsl(var(--text-secondary))]">No hay datos de tendencia todavía.</p>
            ) : trendRows.map((row) => (
              <div key={row.session_id} className="flex items-center justify-between gap-4 rounded-lg bg-[hsl(var(--bg-muted))] dark:bg-black/20 px-4 py-1.5">
                <div className="min-w-0">
                  <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">
                    {new Date(row.session_date + 'T12:00:00').toLocaleDateString('es-CO', { month: 'short', day: 'numeric' })}
                  </p>
                  <p className="text-2xs font-medium text-[hsl(var(--text-secondary))]">{row.status}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{row.attendance_rate}%</p>
                  <p className="text-2xs font-medium text-[hsl(var(--text-secondary))]">{row.present_count}/{row.present_count + row.absent_count}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Alertas</p>
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{repeatAbsentees.length} reincidentes</p>
          </div>
          <div className="space-y-3">
            {alerts.length === 0 && repeatAbsentees.length === 0 ? (
              <p className="text-sm text-[hsl(var(--text-secondary))]">Sin alertas activas.</p>
            ) : (
              <>
                {alerts.map((alert, index) => (
                  <div key={`${alert.type}-${index}`} className="rounded-lg border border-[hsl(var(--warning)/25%)] dark:border-[hsl(var(--warning)/100%)]/30 bg-warning-soft dark:bg-[hsl(var(--warning))]/10 px-4 py-1.5">
                    <p className="text-sm font-bold text-warning-text dark:text-[hsl(var(--warning))]">{alert.message}</p>
                  </div>
                ))}
                {repeatAbsentees.slice(0, 4).map((item) => (
                  <div key={item.persona_id} className="rounded-lg border border-[hsl(var(--danger)/25%)] dark:border-[hsl(var(--danger)/100%)]/30 bg-danger-soft dark:bg-[hsl(var(--danger))]/10 px-4 py-1.5">
                    <p className="text-sm font-bold text-danger-text dark:text-[hsl(var(--danger))]">{item.name}</p>
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--danger))] mt-1">{item.absences} ausencias recurrentes</p>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] flex items-center gap-2">
          <Activity className="text-[hsl(var(--primary))]" size={18} /> Reporte semanal
        </h3>
        <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
          {reportPersonas.length} personas
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="session-topic" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Tema tratado</label>
          <input
            id="session-topic"
            value={reportTopic}
            onChange={(e) => setReportTopic(e.target.value)}
            className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            placeholder="Unidad familiar, fe, oración..."
          />
        </div>
        <div>
          <label htmlFor="session-offering" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Ofrenda recibida</label>
          <input
            type="number"
            id="session-offering"
            value={reportOfferingAmount}
            onChange={(e) => setReportOfferingAmount(e.target.value)}
            className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            placeholder="0"
            min="0"
            step="0.01"
          />
        </div>
        <div>
          <label htmlFor="session-status" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Estado</label>
          <select
            id="session-status"
            value={reportStatus}
            onChange={(e) => {
              const nextStatus =
                e.target.value === 'Cancelada' || e.target.value === 'No realizada' || e.target.value === 'Realizada'
                  ? e.target.value
                  : 'Realizada';
              setReportStatus(nextStatus as 'Realizada' | 'Cancelada' | 'No realizada');
            }}
            className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
          >
            <option value="Realizada">Realizada</option>
            <option value="No realizada">No realizada</option>
            <option value="Cancelada">Cancelada</option>
          </select>
        </div>
        <div>
          <label htmlFor="session-novelty" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Novedad</label>
          <select
            id="session-novelty"
            value={reportNoveltyType}
            onChange={(e) => setReportNoveltyType(e.target.value)}
            className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
          >
            <option value="">Sin novedad</option>
            <option value="weather">Clima</option>
            <option value="work">Trabajo</option>
            <option value="health">Salud</option>
            <option value="family">Familia</option>
            <option value="other">Otro</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="session-novelty-detail" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Detalle de novedad</label>
          <textarea
            id="session-novelty-detail"
            value={reportNoveltyDetail}
            onChange={(e) => setReportNoveltyDetail(e.target.value)}
            className="w-full min-h-24 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg p-4 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            placeholder="Explica la novedad o la razón del ajuste..."
          />
        </div>
        <div>
          <label htmlFor="session-cancellation-reason" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Motivo de cancelación</label>
          <textarea
            id="session-cancellation-reason"
            value={reportCancellationReason}
            onChange={(e) => setReportCancellationReason(e.target.value)}
            className="w-full min-h-24 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg p-4 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            placeholder="Si no se realizó, explica la causa..."
          />
        </div>
      </div>

      <div>
        <label htmlFor="session-notes" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Notas del reporte</label>
        <textarea
          id="session-notes"
          value={reportNotes}
          onChange={(e) => setReportNotes(e.target.value)}
          className="w-full min-h-28 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg p-4 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
          placeholder="Resumen pastoral, acuerdos, seguimiento..."
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Asistencia por persona</h4>
          <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Presente / Ausente</span>
        </div>
        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
          {reportPersonas.map((row) => {
            const attended = row.attended !== false;
            return (
              <div key={row.persona_id} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-4 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{row.name}</p>
                    <p className="text-2xs uppercase font-bold tracking-wide text-[hsl(var(--text-secondary))]">{row.role || 'Persona'}</p>
                  </div>
                  <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                    <input
                      type="checkbox"
                      checked={attended}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setReportPersonas(prev => prev.map(item => item.persona_id === row.persona_id ? {
                          ...item,
                          attended: checked,
                          absence_reason: checked ? null : item.absence_reason || 'other',
                          absence_reason_detail: checked ? null : item.absence_reason_detail || '',
                        } : item));
                      }}
                      className="size-4 rounded border-[hsl(var(--border-primary))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
                    />
                    {attended ? 'Presente' : 'Ausente'}
                  </label>
                </div>

                {!attended && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label htmlFor={`absence-reason-${row.persona_id}`} className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Razón</label>
                      <select
                        id={`absence-reason-${row.persona_id}`}
                        value={row.absence_reason || 'other'}
                        onChange={(e) => setReportPersonas(prev => prev.map(item => item.persona_id === row.persona_id ? { ...item, absence_reason: e.target.value as AttendanceReason } : item))}
                        className="w-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-primary))] rounded-lg py-2.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
                      >
                        {ATTENDANCE_REASON_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                      </select>
                    </div>
                    <div>
                      <label htmlFor={`absence-detail-${row.persona_id}`} className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Detalle</label>
                      <input
                        id={`absence-detail-${row.persona_id}`}
                        value={row.absence_reason_detail || ''}
                        onChange={(e) => setReportPersonas(prev => prev.map(item => item.persona_id === row.persona_id ? { ...item, absence_reason_detail: e.target.value } : item))}
                        className="w-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-primary))] rounded-lg py-2.5 px-4 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
                        placeholder="Especifica el motivo"
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex justify-end">
        {activeSession?.report_deadline && new Date() > new Date(activeSession.report_deadline) ? (
          <div className="flex items-center gap-2 text-[hsl(var(--danger))] bg-danger-soft dark:bg-[hsl(var(--danger))]/10 px-4 py-1.5 rounded-lg">
            <Clock size={16} />
            <span className="text-xs font-semibold uppercase tracking-wide">Plazo de reporte vencido ({new Date(activeSession.report_deadline).toLocaleString()})</span>
          </div>
        ) : (
          <button
            onClick={onSaveReport}
            disabled={savingReport || !activeSession || !activeSessionEnabled}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--success))] hover:bg-[hsl(var(--success))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide transition-all shadow-lg shadow-[hsl(var(--success)/20%)] disabled:opacity-50"
          >
            {savingReport ? <Loader2 className="animate-spin" size={14} /> : <CheckCircle2 size={14} />}
            Guardar reporte
          </button>
        )}
      </div>
    </div>
  );
}

export default GroupMonitoringPanel;
