import { NextResponse } from 'next/server'

const API_BASE = (process.env.API_BASE_URL || process.env.E2E_API_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '')
const PRIMARY_COLLECTION_PATH = '/crm/resources/automation-edges'
const FALLBACK_COLLECTION_PATH = '/crm/resources/automations/edges'

function buildBackendUrl(path: string, request: Request) {
  const backendUrl = new URL(`${API_BASE}${path}`)
  const incomingUrl = new URL(request.url)
  backendUrl.search = incomingUrl.search
  return backendUrl
}

function buildForwardHeaders(request: Request) {
  const headers = new Headers()
  const auth = request.headers.get('authorization')
  const accept = request.headers.get('accept')
  const contentType = request.headers.get('content-type')

  if (auth) headers.set('authorization', auth)
  if (accept) headers.set('accept', accept)
  if (contentType) headers.set('content-type', contentType)

  return headers
}

async function forward(
  request: Request,
  path: string,
  init?: { body?: BodyInit | null },
) {
  const response = await fetch(buildBackendUrl(path, request), {
    method: request.method,
    headers: buildForwardHeaders(request),
    body: init?.body,
    cache: 'no-store',
  })

  const raw = await response.text()
  const contentType = response.headers.get('content-type') || 'application/json'
  return new NextResponse(raw, {
    status: response.status,
    headers: { 'content-type': contentType },
  })
}

export async function proxyAutomationEdgesCollection(request: Request) {
  const body = request.method === 'POST' ? await request.text() : null
  const primary = await forward(request, PRIMARY_COLLECTION_PATH, { body })
  if (primary.status !== 404) {
    return primary
  }
  const fallback = await forward(request, FALLBACK_COLLECTION_PATH, { body })
  if (request.method === 'GET' && fallback.status === 422) {
    // Backends without the dedicated collection route can still resolve this
    // `/automations/{automation_id}` route and emit 422. For builder boot,
    // that should degrade to an empty graph instead of crashing the screen.
    return NextResponse.json([])
  }
  return fallback
}

export async function proxyAutomationEdgesItem(request: Request, edgeId: string) {
  const primary = await forward(request, `${PRIMARY_COLLECTION_PATH}/${edgeId}`)
  if (primary.status !== 404) {
    return primary
  }
  return forward(request, `${FALLBACK_COLLECTION_PATH}/${edgeId}`)
}
