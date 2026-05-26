interface WebVitalMetric {
  id: string;
  name: string;
  value: number;
  label: 'custom' | 'web-vital';
}

type ReportCallback = (metric: WebVitalMetric) => void;

const TRACKED_METRICS = new Set(['TTFB', 'LCP', 'FCP'])

export const reportWebVitals: ReportCallback = (metric) => {
  if (typeof window === 'undefined') return
  if (!TRACKED_METRICS.has(metric.name)) return

  if (process.env.NODE_ENV === 'development') {
    console.info('[web-vitals]', {
      name: metric.name,
      value: metric.value,
      id: metric.id,
      path: window.location.pathname,
    })
  }
}
