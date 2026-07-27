import { ApiError } from '@/lib/http';
import type { AttendancePersona } from './strategies/[id]/strategyDetailShared';

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const detail = error.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object' && 'detail' in detail) {
      return String((detail as { detail?: unknown }).detail || fallback);
    }
  }
  return error instanceof Error ? error.message : fallback;
}

export const toAttendanceStatus = (value: string | undefined): AttendancePersona['status'] =>
  value === 'absent' || value === 'first_time' ? value : 'present';

export const formatLocalDate = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};
