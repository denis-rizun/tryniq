import type { GraphEdge, GraphNode, NodeKind } from './graph-data';

export interface Viewport {
  cx: number;
  cy: number;
  width: number;
  height: number;
}

export type Positions = Map<string, { x: number; y: number }>;

const TAU = Math.PI * 2;
const CHILD_KINDS: ReadonlySet<NodeKind> = new Set(['decision', 'action', 'question']);

const radii = (vp: Viewport) => {
  const base = Math.min(vp.width, vp.height);
  const max = base / 2 - 40;
  const rTopic = Math.min(base * 0.22, max * 0.5);
  const rChild = Math.min(rTopic * 1.85, max * 0.78);
  const rOuter = Math.min(rTopic * 2.6, max);
  return { rTopic, rChild, rOuter };
};

const polar = (cx: number, cy: number, r: number, theta: number) => ({
  x: cx + r * Math.cos(theta),
  y: cy + r * Math.sin(theta),
});

const groupBy = <T, K>(items: T[], key: (t: T) => K): Map<K, T[]> => {
  const out = new Map<K, T[]>();
  for (const item of items) {
    const k = key(item);
    if (!out.has(k)) out.set(k, []);
    out.get(k)!.push(item);
  }
  return out;
};

const buildNeighborMap = (edges: GraphEdge[]): Map<string, Set<string>> => {
  const m = new Map<string, Set<string>>();
  for (const e of edges) {
    if (!m.has(e.from)) m.set(e.from, new Set());
    if (!m.has(e.to)) m.set(e.to, new Set());
    m.get(e.from)!.add(e.to);
    m.get(e.to)!.add(e.from);
  }
  return m;
};

const placeChildrenAroundTopic = (
  children: GraphNode[],
  topicAngle: number,
  vp: Viewport,
  rChild: number,
  out: Positions,
): void => {
  if (children.length === 0) return;
  const arc = Math.min(TAU / 8, 0.08 + 0.06 * children.length);
  for (let i = 0; i < children.length; i++) {
    const offset = children.length === 1 ? 0 : (i / (children.length - 1) - 0.5) * arc;
    const { x, y } = polar(vp.cx, vp.cy, rChild, topicAngle + offset);
    out.set(children[i].id, { x, y });
  }
};

const placeOuterRing = (
  items: GraphNode[],
  vp: Viewport,
  r: number,
  startAngle: number,
  endAngle: number,
  out: Positions,
): void => {
  if (items.length === 0) return;
  const sorted = [...items].sort((a, b) => a.label.localeCompare(b.label));
  const span = endAngle - startAngle;
  const step = sorted.length === 1 ? 0 : span / sorted.length;
  for (let i = 0; i < sorted.length; i++) {
    const angle = startAngle + step * (i + 0.5);
    const { x, y } = polar(vp.cx, vp.cy, r, angle);
    out.set(sorted[i].id, { x, y });
  }
};

export const tidyLayout = (nodes: GraphNode[], edges: GraphEdge[], vp: Viewport): Positions => {
  const { rTopic, rChild, rOuter } = radii(vp);
  const out: Positions = new Map();

  const byKind = groupBy(nodes, (n) => n.kind);
  const meeting = byKind.get('meeting') ?? [];
  const topics = (byKind.get('topic') ?? []).slice().sort((a, b) => a.t - b.t);
  const children = nodes.filter((n) => CHILD_KINDS.has(n.kind));
  const persons = byKind.get('person') ?? [];
  const entities = byKind.get('entity') ?? [];

  for (const m of meeting) out.set(m.id, { x: vp.cx, y: vp.cy });

  const topicAngles = new Map<string, number>();
  if (topics.length > 0) {
    const step = TAU / topics.length;
    for (let i = 0; i < topics.length; i++) {
      const angle = -Math.PI / 2 + step * i;
      topicAngles.set(topics[i].id, angle);
      const { x, y } = polar(vp.cx, vp.cy, rTopic, angle);
      out.set(topics[i].id, { x, y });
    }
  }

  const neighbors = buildNeighborMap(edges);
  const topicForChild = new Map<string, string>();
  for (const child of children) {
    const ns = neighbors.get(child.id);
    if (!ns) continue;
    for (const m of ns) {
      if (topicAngles.has(m)) {
        topicForChild.set(child.id, m);
        break;
      }
    }
  }

  const childrenByTopic = groupBy(
    children.filter((c) => topicForChild.has(c.id)),
    (c) => topicForChild.get(c.id)!,
  );
  for (const [topicId, group] of childrenByTopic) {
    const angle = topicAngles.get(topicId);
    if (angle === undefined) continue;
    placeChildrenAroundTopic(group, angle, vp, rChild, out);
  }

  const orphans = children.filter((c) => !topicForChild.has(c.id));
  placeOuterRing(orphans, vp, rChild, Math.PI - 0.4, Math.PI + 0.4, out);

  placeOuterRing(persons, vp, rOuter, -Math.PI + 0.05, -0.05, out);
  placeOuterRing(entities, vp, rOuter, 0.05, Math.PI - 0.05, out);

  return out;
};
