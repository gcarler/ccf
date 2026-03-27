type ReportPayload = {
  id: string
  name: string
  value: number
  label: 'web-vital' | 'custom'
  page: string
  path: string
  timestamp: number
}

function sendBeacon(url: string, body: Blob) {
  if (navigator.sendBeacon) {
    navigator.sendBeacon(url, body)
  } else {
    fetch(url, {
      body,
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}

export function reportWebVital(metric: Pick<ReportPayload, 'id' | 'name' | 'value' | 'label'>) {
  const payload: ReportPayload = {
    ...metric,
    page: document.title,
    path: window.location.pathname,
    timestamp: Date.now(),
  }

  const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' })
  sendBeacon('/api/analytics/web-vitals', blob)
}
