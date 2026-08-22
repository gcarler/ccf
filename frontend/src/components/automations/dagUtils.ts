import { Edge, Node } from '@xyflow/react';
import { apiFetch } from '@/lib/http';

export interface CycleCheckResult {
  hasCycle: boolean;
  error?: string;
}

/**
 * Detects if adding an edge from source to target would create a cycle in the DAG.
 * Returns true if a cycle is detected.
 */
export function wouldCreateCycle(
  sourceId: string,
  targetId: string,
  existingEdges: Edge[]
): CycleCheckResult {
  // 1. Direct self loop
  if (sourceId === targetId) {
    return {
      hasCycle: true,
      error: 'Un nodo no puede conectarse consigo mismo.',
    };
  }

  // 2. Build adjacency list of existing graph
  const adj = new Map<string, string[]>();
  for (const edge of existingEdges) {
    if (!edge.source || !edge.target) continue;
    const targets = adj.get(edge.source) || [];
    targets.push(edge.target);
    adj.set(edge.source, targets);
  }

  // 3. BFS / DFS from targetId to see if sourceId is reachable
  const visited = new Set<string>();
  const queue = [targetId];

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (current === sourceId) {
      return {
        hasCycle: true,
        error: 'Conexión inválida: crearía un ciclo en el flujo (violación de DAG).',
      };
    }

    if (!visited.has(current)) {
      visited.add(current);
      const neighbors = adj.get(current) || [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          queue.push(neighbor);
        }
      }
    }
  }

  return { hasCycle: false };
}

/**
 * Validate entire graph client-side using Kahn's algorithm (Topological sort).
 */
export function validateGraphDAG(nodes: Node[], edges: Edge[]): CycleCheckResult {
  if (nodes.length === 0) return { hasCycle: false };

  const inDegree = new Map<string, number>();
  const adj = new Map<string, string[]>();

  for (const node of nodes) {
    inDegree.set(node.id, 0);
    adj.set(node.id, []);
  }

  for (const edge of edges) {
    if (!inDegree.has(edge.source) || !inDegree.has(edge.target)) continue;
    if (edge.source === edge.target) {
      return {
        hasCycle: true,
        error: `El nodo "${edge.source}" tiene una auto-conexión cíclica.`,
      };
    }
    const currentIn = inDegree.get(edge.target) || 0;
    inDegree.set(edge.target, currentIn + 1);

    const neighbors = adj.get(edge.source) || [];
    neighbors.push(edge.target);
    adj.set(edge.source, neighbors);
  }

  const queue: string[] = [];
  for (const [nodeId, degree] of inDegree.entries()) {
    if (degree === 0) {
      queue.push(nodeId);
    }
  }

  let visitedCount = 0;
  while (queue.length > 0) {
    const u = queue.shift()!;
    visitedCount++;

    const neighbors = adj.get(u) || [];
    for (const v of neighbors) {
      const newDegree = (inDegree.get(v) || 1) - 1;
      inDegree.set(v, newDegree);
      if (newDegree === 0) {
        queue.push(v);
      }
    }
  }

  if (visitedCount !== nodes.length) {
    return {
      hasCycle: true,
      error: 'El flujo contiene uno o más ciclos de ejecución cerrados.',
    };
  }

  return { hasCycle: false };
}

/**
 * Validate graph with backend endpoint /api/crm/automations/flows/check-cycles
 */
export async function validateFlowWithServer(
  nodes: Node[],
  edges: Edge[],
  token: string
): Promise<{ valid: boolean; error?: string }> {
  try {
    const payload = {
      flow_data: {
        nodes: nodes.map((n) => ({ id: n.id })),
        edges: edges.map((e) => ({ source: e.source, target: e.target })),
      },
    };

    const response = await apiFetch<{ cycles?: string[][] }>('/crm/automations/flows/check-cycles', {
      method: 'POST',
      token,
      body: payload,
    });

    if (response.cycles && response.cycles.length > 0) {
      return {
        valid: false,
        error: `Ciclo detectado por el motor: ${response.cycles.map((c) => c.join(' -> ')).join('; ')}`,
      };
    }

    return { valid: true };
  } catch (err: any) {
    return { valid: false, error: err?.message || 'Error al validar flujo en el servidor' };
  }
}
