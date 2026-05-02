import { colorFor, type GraphEdge, type GraphNode, NODES, radiusFor } from './graph-data';

interface GraphSVGProps {
  visibleNodes: GraphNode[];
  visibleEdges: GraphEdge[];
  selected: GraphNode | null;
  onSelect: (n: GraphNode) => void;
}

const trim = (s: string): string => (s.length > 28 ? `${s.slice(0, 26)}…` : s);

export const GraphSVG = ({ visibleNodes, visibleEdges, selected, onSelect }: GraphSVGProps) => (
  <svg
    viewBox="0 0 800 520"
    preserveAspectRatio="xMidYMid meet"
    style={{ width: '100%', height: 'calc(100% - 14px)', position: 'absolute', top: 14, left: 0 }}
    role="img"
    aria-label="Knowledge graph"
  >
    <title>Knowledge graph</title>
    {visibleEdges.map((e, i) => {
      const a = NODES.find((n) => n.id === e.from);
      const b = NODES.find((n) => n.id === e.to);
      if (!a || !b) return null;
      return (
        <line
          key={i}
          x1={a.x}
          y1={a.y}
          x2={b.x}
          y2={b.y}
          stroke={e.plum ? 'var(--color-entity)' : 'rgba(26,24,21,0.18)'}
          strokeWidth={1}
          strokeDasharray={e.dashed ? '4 3' : ''}
        />
      );
    })}
    {visibleNodes.map((n) => {
      const fill = colorFor(n.kind);
      const r = radiusFor(n.kind);
      const dashed = n.status === 'provisional';
      const isSelected = selected?.id === n.id;
      return (
        <g key={n.id} style={{ cursor: 'pointer' }} onClick={() => onSelect(n)}>
          {isSelected && (
            <circle
              cx={n.x}
              cy={n.y}
              r={r + 6}
              fill="none"
              stroke="var(--color-accent-500)"
              strokeWidth="2"
            />
          )}
          <circle
            cx={n.x}
            cy={n.y}
            r={r}
            fill={fill}
            stroke={n.ownerless ? 'var(--color-action)' : '#FFFFFF'}
            strokeWidth={n.ownerless ? 1.5 : n.status === 'confirmed' ? 1.5 : 1}
            strokeDasharray={dashed ? '3 2' : ''}
            opacity={n.status === 'superseded' ? 0.4 : 1}
          />
          <text
            x={n.x}
            y={n.y + r + 14}
            textAnchor="middle"
            fontSize="11"
            fill="var(--color-ink)"
            fontFamily="var(--font-sans)"
            style={{ pointerEvents: 'none' }}
          >
            {trim(n.label)}
          </text>
        </g>
      );
    })}
  </svg>
);
