import type { SimLink, SimNode } from '@/lib/hooks/use-graph-simulation';

interface GraphEdgeProps {
  edge: SimLink;
  index: number;
  focused: boolean;
  dimmed: boolean;
}

export const GraphEdgeView = ({ edge, index, focused, dimmed }: GraphEdgeProps) => {
  const source = edge.source as SimNode;
  const target = edge.target as SimNode;
  if (!source || !target || source.x == null || target.x == null) return null;
  return (
    <line
      key={`${edge.raw.from}-${edge.raw.to}-${index}`}
      x1={source.x}
      y1={source.y ?? 0}
      x2={target.x}
      y2={target.y ?? 0}
      stroke={edge.raw.plum ? 'var(--color-entity)' : 'var(--color-ink)'}
      strokeOpacity={dimmed ? (focused ? 0.55 : 0.05) : 0.22}
      strokeWidth={focused ? 1.4 : 1}
      strokeDasharray={edge.raw.dashed ? '4 3' : ''}
      style={{ transition: 'stroke-opacity 200ms ease-out, stroke-width 200ms ease-out' }}
    />
  );
};
