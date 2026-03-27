'use client';

import { useReportWebVitals } from 'next/web-vitals';
import { reportWebVitals } from '@/app/reportWebVitals';

export function WebVitalsReporter() {
  useReportWebVitals(reportWebVitals);
  return null;
}
