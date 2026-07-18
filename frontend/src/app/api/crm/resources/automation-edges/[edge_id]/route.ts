import { proxyAutomationEdgesItem } from '../_shared'

export const runtime = 'nodejs'

type RouteContext = {
  params: Promise<{ edge_id: string }>
}

export async function DELETE(request: Request, context: RouteContext) {
  const { edge_id } = await context.params
  return proxyAutomationEdgesItem(request, edge_id)
}
