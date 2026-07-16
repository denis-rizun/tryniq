import { radiusFor, type SimNode } from '@/lib/hooks/use-graph-simulation';
import type { GraphNode } from './graph-data';
import { colorFor } from './graph-data';

interface GraphNodeViewProps {
  dragging: boolean;
  enter: number;
  focused: boolean;
  node: SimNode;
  selected: GraphNode | null;
  showLabel: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  onPointerDown: (event: React.PointerEvent<SVGGElement>) => void;
  onPointerMove: (event: React.PointerEvent<SVGGElement>) => void;
  onPointerUp: (event: React.PointerEvent<SVGGElement>) => void;
  onSelect: (event: React.MouseEvent<SVGGElement>) => void;
}

const trim = (label: string): string => (label.length > 26 ? `${label.slice(0, 24)}…` : label);

export const GraphNodeView = ({
  dragging,
  enter,
  focused,
  node,
  selected,
  showLabel,
  onMouseEnter,
  onMouseLeave,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onSelect,
}: GraphNodeViewProps) => {
  const radius = radiusFor(node.kind);
  const selectedNode = selected?.id === node.id;
  const opacity = focused ? 1 : 0.18;
  return (
    <g
      className="node"
      transform={`translate(${node.x ?? 0},${node.y ?? 0})`}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onClick={onSelect}
      style={{ cursor: dragging ? 'grabbing' : 'pointer', opacity: opacity * enter }}
    >
      {selectedNode && (
        <circle
          r={radius + 6}
          fill="none"
          stroke="var(--color-accent-500)"
          strokeWidth={1.5}
          opacity={0.7}
        />
      )}
      <circle
        r={radius * (0.4 + 0.6 * enter)}
        fill={colorFor(node.kind)}
        stroke={node.ownerless ? 'var(--color-action)' : '#FFFFFF'}
        strokeWidth={node.ownerless ? 1.5 : 1.2}
        strokeDasharray={node.status === 'provisional' ? '3 2' : ''}
        opacity={node.status === 'superseded' ? 0.45 : 1}
        style={{ transition: 'r 250ms ease-out' }}
      />
      {showLabel && (
        <text
          y={radius + 12}
          textAnchor="middle"
          fontSize={11}
          fill="var(--color-ink)"
          fontFamily="var(--font-sans)"
          style={{ pointerEvents: 'none', opacity: enter }}
        >
          {trim(node.label)}
        </text>
      )}
    </g>
  );
};
