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
  x?: number;
  y?: number;
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

export const colorFor = (kind: NodeKind): string =>
  ({
    decision: 'var(--color-decision)',
    action: 'var(--color-action)',
    question: 'var(--color-question)',
    entity: 'var(--color-entity)',
    person: '#7E8C5B',
    topic: '#6B6358',
    meeting: '#3F4A3A',
  })[kind] || '#6B6358';
