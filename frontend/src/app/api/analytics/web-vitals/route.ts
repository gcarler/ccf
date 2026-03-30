import { NextResponse } from 'next/server'
import { persistWebVital, readWebVitals, summarizeWebVitals } from '@/lib/server/webVitalsStore'

export const runtime = 'nodejs'

export async function POST(request: Request) {
  const payload = await request.json().catch(() => null)
  if (!payload) {
    return NextResponse.json({ status: 'ignored', reason: 'empty-payload' })
  }

  const result = await persistWebVital(payload)
  if (!result.ok) {
    return NextResponse.json({ status: 'ignored', reason: result.reason })
  }

  console.info('[web-vitals]', payload)
  return NextResponse.json({ status: 'ok' })
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const limitParam = Number(searchParams.get('limit') || 200)
  const name = searchParams.get('name') || undefined
  const path = searchParams.get('path') || undefined
  const records = await readWebVitals({
    limit: Number.isFinite(limitParam) ? limitParam : 200,
    name,
    path,
  })

  return NextResponse.json({
    status: 'ok',
    count: records.length,
    summary: summarizeWebVitals(records),
    records,
  })
}
