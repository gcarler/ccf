import { mkdir, readFile, appendFile } from 'node:fs/promises'
import path from 'node:path'

export type StoredWebVital = {
  id: string
  name: 'TTFB' | 'LCP' | 'FCP'
  value: number
  label: 'web-vital' | 'custom'
  page: string
  path: string
  timestamp: number
}

const DATA_DIR = path.join(process.cwd(), 'analytics')
const DATA_FILE = path.join(DATA_DIR, 'web-vitals.ndjson')
const ALLOWED_NAMES = new Set(['TTFB', 'LCP', 'FCP'])

function isValid(payload: unknown): payload is StoredWebVital {
  if (!payload || typeof payload !== 'object') return false
  const candidate = payload as Partial<StoredWebVital>
  if (typeof candidate.id !== 'string' || !candidate.id.trim()) return false
  if (typeof candidate.name !== 'string' || !ALLOWED_NAMES.has(candidate.name)) return false
  if (typeof candidate.value !== 'number' || Number.isNaN(candidate.value)) return false
  if (candidate.label !== 'web-vital' && candidate.label !== 'custom') return false
  if (typeof candidate.page !== 'string') return false
  if (typeof candidate.path !== 'string') return false
  if (typeof candidate.timestamp !== 'number' || candidate.timestamp <= 0) return false
  return true
}

export async function persistWebVital(payload: unknown) {
  if (!isValid(payload)) return { ok: false as const, reason: 'invalid-payload' as const }
  await mkdir(DATA_DIR, { recursive: true })
  await appendFile(DATA_FILE, `${JSON.stringify(payload)}\n`, 'utf8')
  return { ok: true as const }
}

export async function readWebVitals(options: { limit?: number; name?: string; path?: string } = {}) {
  const { limit = 200, name, path: pathFilter } = options
  const clampedLimit = Math.min(Math.max(limit, 1), 2000)
  let content = ''
  try {
    content = await readFile(DATA_FILE, 'utf8')
  } catch {
    return [] as StoredWebVital[]
  }

  const records = content
    .split('\n')
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line) as unknown
      } catch {
        return null
      }
    })
    .filter((entry): entry is StoredWebVital => isValid(entry))

  const filtered = records.filter((entry) => {
    if (name && entry.name !== name) return false
    if (pathFilter && entry.path !== pathFilter) return false
    return true
  })

  return filtered.slice(-clampedLimit)
}

export function summarizeWebVitals(records: StoredWebVital[]) {
  const byMetric: Record<string, number[]> = {}
  for (const row of records) {
    if (!byMetric[row.name]) byMetric[row.name] = []
    byMetric[row.name].push(row.value)
  }

  const quantile = (values: number[], q: number) => {
    if (!values.length) return null
    const sorted = [...values].sort((a, b) => a - b)
    const idx = Math.floor((sorted.length - 1) * q)
    return Math.round(sorted[idx] * 100) / 100
  }

  const summary: Record<string, { count: number; p50: number | null; p75: number | null; latest: number | null }> = {}
  for (const [metric, values] of Object.entries(byMetric)) {
    summary[metric] = {
      count: values.length,
      p50: quantile(values, 0.5),
      p75: quantile(values, 0.75),
      latest: values.length ? Math.round(values[values.length - 1] * 100) / 100 : null,
    }
  }

  return summary
}
