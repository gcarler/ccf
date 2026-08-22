/**
 * Empirical stress test for Frontend DAG algorithms in dagUtils.ts:
 * - wouldCreateCycle (incremental edge cycle detection)
 * - validateGraphDAG (Kahn's topological sort cycle validation)
 * - Adversarial test cases: self-loops, 2-node cycles, 3-node cycles, multi-branch, diamonds, disconnected, 1,000 nodes.
 */

// Implementation of wouldCreateCycle matching dagUtils.ts
function wouldCreateCycle(sourceId, targetId, existingEdges) {
  if (sourceId === targetId) {
    return {
      hasCycle: true,
      error: 'Un nodo no puede conectarse consigo mismo.',
    };
  }

  const adj = new Map();
  for (const edge of existingEdges) {
    if (!edge.source || !edge.target) continue;
    const targets = adj.get(edge.source) || [];
    targets.push(edge.target);
    adj.set(edge.source, targets);
  }

  const visited = new Set();
  const queue = [targetId];

  while (queue.length > 0) {
    const current = queue.shift();
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

// Implementation of validateGraphDAG matching dagUtils.ts
function validateGraphDAG(nodes, edges) {
  if (nodes.length === 0) return { hasCycle: false };

  const inDegree = new Map();
  const adj = new Map();

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

  const queue = [];
  for (const [nodeId, degree] of inDegree.entries()) {
    if (degree === 0) {
      queue.push(nodeId);
    }
  }

  let visitedCount = 0;
  while (queue.length > 0) {
    const u = queue.shift();
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

// Test runner
let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    failed++;
    throw new Error(message);
  } else {
    console.log(`✅ PASS: ${message}`);
    passed++;
  }
}

console.log("=== RUNNING FRONTEND DAG STRESS TESTS ===");

// 1. wouldCreateCycle: Self-loop
{
  const res = wouldCreateCycle('A', 'A', []);
  assert(res.hasCycle === true, 'Self-loop detected');
}

// 2. wouldCreateCycle: Direct reverse edge cycle
{
  const edges = [{ source: 'A', target: 'B' }];
  const res = wouldCreateCycle('B', 'A', edges);
  assert(res.hasCycle === true, 'Direct reverse edge cycle detected');
}

// 3. wouldCreateCycle: 3-hop indirect cycle
{
  const edges = [
    { source: 'A', target: 'B' },
    { source: 'B', target: 'C' },
    { source: 'C', target: 'D' },
  ];
  const res = wouldCreateCycle('D', 'A', edges);
  assert(res.hasCycle === true, '3-hop indirect cycle detected');
}

// 4. wouldCreateCycle: Valid forward addition in Diamond
{
  const edges = [
    { source: 'A', target: 'B' },
    { source: 'A', target: 'C' },
    { source: 'B', target: 'D' },
  ];
  const res = wouldCreateCycle('C', 'D', edges);
  assert(res.hasCycle === false, 'Diamond forward edge allowed without cycle');
}

// 5. validateGraphDAG: Empty graph
{
  const res = validateGraphDAG([], []);
  assert(res.hasCycle === false, 'Empty graph is acyclic');
}

// 6. validateGraphDAG: Single node
{
  const res = validateGraphDAG([{ id: 'A' }], []);
  assert(res.hasCycle === false, 'Single node is acyclic');
}

// 7. validateGraphDAG: Disconnected with isolated cycle
{
  const nodes = [
    { id: 'A1' }, { id: 'A2' }, { id: 'A3' },
    { id: 'C1' }, { id: 'C2' }, { id: 'C3' },
    { id: 'I1' }, { id: 'I2' }
  ];
  const edges = [
    { source: 'A1', target: 'A2' },
    { source: 'A2', target: 'A3' },
    { source: 'C1', target: 'C2' },
    { source: 'C2', target: 'C3' },
    { source: 'C3', target: 'C1' },
  ];
  const res = validateGraphDAG(nodes, edges);
  assert(res.hasCycle === true, 'Disconnected graph with isolated cycle detected');
}

// 8. validateGraphDAG: Diamond DAG
{
  const nodes = [{ id: 'A' }, { id: 'B' }, { id: 'C' }, { id: 'D' }];
  const edges = [
    { source: 'A', target: 'B' },
    { source: 'A', target: 'C' },
    { source: 'B', target: 'D' },
    { source: 'C', target: 'D' },
  ];
  const res = validateGraphDAG(nodes, edges);
  assert(res.hasCycle === false, 'Diamond DAG is valid and acyclic');
}

// 9. Performance test: 1,000 nodes DAG
{
  const N = 1000;
  const nodes = Array.from({ length: N }, (_, i) => ({ id: `node_${i}` }));
  const edges = [];
  for (let i = 0; i < N - 1; i++) {
    edges.push({ source: `node_${i}`, target: `node_${i + 1}` });
    if (i + 4 < N) edges.push({ source: `node_${i}`, target: `node_${i + 4}` });
  }

  const start = performance.now();
  const res = validateGraphDAG(nodes, edges);
  const timeMs = performance.now() - start;

  assert(res.hasCycle === false, `1,000 nodes DAG validated as acyclic in ${timeMs.toFixed(2)}ms`);
  assert(timeMs < 50, `Performance within budget (<50ms): ${timeMs.toFixed(2)}ms`);
}

// 10. Performance test: 1,000 nodes with deep cycle
{
  const N = 1000;
  const nodes = Array.from({ length: N }, (_, i) => ({ id: `node_${i}` }));
  const edges = Array.from({ length: N - 1 }, (_, i) => ({ source: `node_${i}`, target: `node_${i + 1}` }));
  edges.push({ source: 'node_999', target: 'node_200' });

  const start = performance.now();
  const res = validateGraphDAG(nodes, edges);
  const timeMs = performance.now() - start;

  assert(res.hasCycle === true, `1,000 nodes deep cycle detected in ${timeMs.toFixed(2)}ms`);
  assert(timeMs < 50, `Cycle detection within budget (<50ms): ${timeMs.toFixed(2)}ms`);
}

console.log(`\n=== RESULT: ${passed} passed, ${failed} failed ===`);
if (failed > 0) process.exit(1);
