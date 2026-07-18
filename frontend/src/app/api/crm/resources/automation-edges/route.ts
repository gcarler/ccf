import { proxyAutomationEdgesCollection } from './_shared'

export const runtime = 'nodejs'

export async function GET(request: Request) {
  return proxyAutomationEdgesCollection(request)
}

export async function POST(request: Request) {
  return proxyAutomationEdgesCollection(request)
}
