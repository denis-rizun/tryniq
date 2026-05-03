import type {
  GraphEdgeRead,
  GraphEdgeType,
  GraphNodeRead,
  GraphNodeType,
  GraphResponse,
} from '@/lib/api/types';
import type { GraphEdge, GraphNode, NodeKind, NodeStatus } from '@/components/meeting/graph/graph-data';

const KIND_BY_TYPE: Record<GraphNodeType, NodeKind> = {
  Meeting: 'meeting',
  Person: 'person',
  Topic: 'topic',
  Decision: 'decision',
  ActionItem: 'action',
  OpenQuestion: 'question',
  Entity: 'entity',
  Utterance: 'entity',
};

const labelFor = (n: GraphNodeRead): string => {
  const f = n.fields ?? {};
  const candidate = f.text ?? f.title ?? f.name ?? f.summary;
  if (typeof candidate === 'string' && candidate.trim()) return candidate;
  return `${n.type} ${n.id.slice(0, 8)}`;
};

const ownerlessFor = (n: GraphNodeRead, edges: GraphEdgeRead[]): boolean => {
  if (n.type !== 'ActionItem' && n.type !== 'Decision') return false;
  return !edges.some((e) => e.from_id === n.id && (e.type === 'ASSIGNED_TO' || e.type === 'MADE_DECISION'));
};

const utteranceTime = (n: GraphNodeRead): number | null => {
  const t = n.fields?.t_start;
  return typeof t === 'number' ? t : null;
};

const computeNodeTimes = (graph: GraphResponse): Record<string, number> => {
  const utteranceTimes = new Map<string, number>();
  for (const n of graph.nodes) {
    if (n.type !== 'Utterance') continue;
    const t = utteranceTime(n);
    if (t !== null) utteranceTimes.set(n.id, t);
  }

  if (utteranceTimes.size === 0) {
    const fallback: Record<string, number> = {};
    for (const n of graph.nodes) fallback[n.id] = 0;
    return fallback;
  }

  const tMin = Math.min(...utteranceTimes.values());
  const tMax = Math.max(...utteranceTimes.values());
  const span = Math.max(tMax - tMin, 1);
  const norm = (raw: number) => (raw - tMin) / span;

  const adjacency = new Map<string, Set<string>>();
  for (const e of graph.edges) {
    if (!adjacency.has(e.from_id)) adjacency.set(e.from_id, new Set());
    if (!adjacency.has(e.to_id)) adjacency.set(e.to_id, new Set());
    adjacency.get(e.from_id)!.add(e.to_id);
    adjacency.get(e.to_id)!.add(e.from_id);
  }

  const earliest = new Map<string, number>();
  for (const [id, t] of utteranceTimes) earliest.set(id, t);

  for (let iter = 0; iter < 6; iter++) {
    let changed = false;
    for (const n of graph.nodes) {
      const neighbors = adjacency.get(n.id);
      if (!neighbors) continue;
      let best = earliest.get(n.id) ?? Infinity;
      for (const m of neighbors) {
        const other = earliest.get(m);
        if (other !== undefined && other < best) best = other;
      }
      const prev = earliest.get(n.id);
      if (best !== Infinity && (prev === undefined || best < prev)) {
        earliest.set(n.id, best);
        changed = true;
      }
    }
    if (!changed) break;
  }

  const out: Record<string, number> = {};
  for (const n of graph.nodes) {
    if (n.type === 'Meeting') {
      out[n.id] = 0;
      continue;
    }
    const t = earliest.get(n.id);
    out[n.id] = t === undefined ? 0 : norm(t);
  }
  return out;
};

export const adaptGraph = (graph: GraphResponse): { nodes: GraphNode[]; edges: GraphEdge[] } => {
  const times = computeNodeTimes(graph);
  const nodes = graph.nodes.filter((n) => n.type !== 'Utterance');
  const visibleIds = new Set(nodes.map((n) => n.id));

  const uiNodes: GraphNode[] = nodes.map((n) => ({
    id: n.id,
    kind: KIND_BY_TYPE[n.type],
    label: labelFor(n),
    x: 0,
    y: 0,
    status: n.status as NodeStatus,
    t: times[n.id] ?? 0,
    ownerless: ownerlessFor(n, graph.edges),
  }));

  const edgeKindLabel: Partial<Record<GraphEdgeType, string>> = {
    ASSIGNED_TO: 'assigned',
    MADE_DECISION: 'made_by',
    ABOUT_TOPIC: 'about',
    MENTIONS: 'mentions',
    SOURCE: 'source',
    RELATES_TO: 'relates_to',
    BLOCKS: 'blocks',
    DISCUSSED_IN: 'discussed_in',
    PARTICIPATED_IN: 'participated_in',
  };

  const uiEdges: GraphEdge[] = graph.edges
    .filter((e) => visibleIds.has(e.from_id) && visibleIds.has(e.to_id))
    .map((e) => ({
      from: e.from_id,
      to: e.to_id,
      kind: edgeKindLabel[e.type],
      dashed: e.type === 'RELATES_TO',
      plum: e.type === 'RELATES_TO',
    }));

  return { nodes: uiNodes, edges: uiEdges };
};
