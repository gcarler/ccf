import type { ReportCallback } from 'next/dist/compiled/web-vitals'
import { reportWebVital } from '@/lib/vitals'

const TRACKED_METRICS = new Set(['TTFB', 'LCP', 'FCP'])

export const reportWebVitals: ReportCallback = (metric) => {
  if (typeof window === 'undefined') return
  if (!TRACKED_METRICS.has(metric.name)) return

  console.info('[web-vitals:client]', {
    name: metric.name,
    value: metric.value,
    id: metric.id,
    path: window.location.pathname,
  })

  reportWebVital({
    id: metric.id,
    name: metric.name,
    value: metric.value,
    label: metric.label,
  })
}
