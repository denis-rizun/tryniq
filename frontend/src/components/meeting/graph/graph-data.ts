export type NodeKind =
  | 'topic'
  | 'decision'
  | 'action'
  | 'question'
  | 'person'
  | 'meeting'
  | 'entity';
export type NodeStatus = 'provisional' | 'confirmed' | 'superseded';

export interface GraphNode {
  id: string;
  kind: NodeKind;
  label: string;
  x: number;
  y: number;
  status: NodeStatus;
  t: number;
  ownerless?: boolean;
}

export interface GraphEdge {
  from: string;
  to: string;
  kind?: string;
  dashed?: boolean;
  plum?: boolean;
}

export const NODES: GraphNode[] = [
  {
    id: 't1',
    kind: 'topic',
    label: 'eu-west-1 rollout',
    x: 400,
    y: 260,
    status: 'confirmed',
    t: 0.05,
  },
  { id: 't2', kind: 'topic', label: 'payment flow', x: 250, y: 180, status: 'confirmed', t: 0.1 },
  {
    id: 't3',
    kind: 'topic',
    label: 'canary monitoring',
    x: 560,
    y: 180,
    status: 'confirmed',
    t: 0.3,
  },
  { id: 't4', kind: 'topic', label: 'migration shim', x: 270, y: 360, status: 'confirmed', t: 0.2 },
  {
    id: 'd1',
    kind: 'decision',
    label: 'Roll back eu-west-1',
    x: 410,
    y: 100,
    status: 'confirmed',
    t: 0.4,
    ownerless: false,
  },
  {
    id: 'd2',
    kind: 'decision',
    label: 'Improve canary monitoring',
    x: 660,
    y: 100,
    status: 'confirmed',
    t: 0.5,
    ownerless: true,
  },
  {
    id: 'a1',
    kind: 'action',
    label: 'Investigate migration script',
    x: 140,
    y: 280,
    status: 'confirmed',
    t: 0.45,
  },
  {
    id: 'a2',
    kind: 'action',
    label: 'Pull CI history',
    x: 110,
    y: 400,
    status: 'confirmed',
    t: 0.55,
  },
  {
    id: 'a3',
    kind: 'action',
    label: 'Draft postmortem',
    x: 580,
    y: 410,
    status: 'provisional',
    t: 0.95,
  },
  {
    id: 'q1',
    kind: 'question',
    label: 'Regression case missing or skipped?',
    x: 250,
    y: 100,
    status: 'confirmed',
    t: 0.35,
  },
  { id: 'p_mike', kind: 'person', label: 'Mike Torres', x: 110, y: 180, status: 'confirmed', t: 0 },
  { id: 'p_sarah', kind: 'person', label: 'Sarah Chen', x: 700, y: 280, status: 'confirmed', t: 0 },
  { id: 'p_anna', kind: 'person', label: 'Anna Petrov', x: 700, y: 400, status: 'confirmed', t: 0 },
  {
    id: 'pm_001',
    kind: 'meeting',
    label: 'Apr 24 · Payment flow review',
    x: 90,
    y: 80,
    status: 'confirmed',
    t: 0,
  },
];

export const EDGES: GraphEdge[] = [
  { from: 't1', to: 'd1', kind: 'has_decision' },
  { from: 't1', to: 't2' },
  { from: 't1', to: 't3' },
  { from: 't1', to: 't4' },
  { from: 't2', to: 't4' },
  { from: 't3', to: 'd2' },
  { from: 'd1', to: 'a1', kind: 'spawns' },
  { from: 'a1', to: 'a2' },
  { from: 'a1', to: 'p_mike', kind: 'assigned' },
  { from: 'a2', to: 'p_mike', kind: 'assigned' },
  { from: 'd1', to: 'p_mike', kind: 'made_by' },
  { from: 'a3', to: 'p_sarah', kind: 'assigned' },
  { from: 'd1', to: 'p_anna', kind: 'confirmed_by' },
  { from: 't1', to: 'q1' },
  { from: 't2', to: 'pm_001', kind: 'relates_to', dashed: true, plum: true },
];

export const colorFor = (kind: NodeKind): string =>
  ({
    decision: 'var(--color-decision)',
    action: 'var(--color-action)',
    question: 'var(--color-question)',
    entity: 'var(--color-entity)',
    person: 'var(--color-entity)',
    topic: '#6B6358',
    meeting: '#8A7B5C',
  })[kind] || '#6B6358';

export const radiusFor = (kind: NodeKind): number =>
  kind === 'topic' ? 8 : kind === 'person' ? 9 : kind === 'meeting' ? 7 : 11;
