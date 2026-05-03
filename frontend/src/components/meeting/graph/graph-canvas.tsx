'use client';

import { select } from 'd3-selection';
import { zoom, zoomIdentity, type ZoomBehavior } from 'd3-zoom';
import { useEffect, useMemo, useRef, useState } from 'react';
import { type SimLink, type SimNode, radiusFor } from '@/lib/hooks/use-graph-simulation';
import { colorFor, type GraphEdge, type GraphNode } from './graph-data';

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  simNodes: SimNode[];
  simLinks: SimLink[];
  pin: (id: string, x: number | null, y: number | null) => void;
  selected: GraphNode | null;
  onSelect: (n: GraphNode | null) => void;
  width: number;
  height: number;
}

const trim = (s: string): string => (s.length > 26 ? `${s.slice(0, 24)}…` : s);

export const GraphCanvas = ({
  nodes,
  edges,
  simNodes,
  simLinks,
  pin,
  selected,
  onSelect,
  width,
  height,
}: GraphCanvasProps) => {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [transform, setTransform] = useState({ k: 1, x: 0, y: 0 });
  const transformRef = useRef(transform);
  transformRef.current = transform;

  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const draggingIdRef = useRef<string | null>(null);
  draggingIdRef.current = draggingId;

  const seenIdsRef = useRef<Set<string>>(new Set());
  const [appearedAt] = useState<Map<string, number>>(() => new Map());

  const adjacency = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const e of edges) {
      if (!map.has(e.from)) map.set(e.from, new Set());
      if (!map.has(e.to)) map.set(e.to, new Set());
      map.get(e.from)!.add(e.to);
      map.get(e.to)!.add(e.from);
    }
    return map;
  }, [edges]);

  useEffect(() => {
    const now = performance.now();
    for (const n of nodes) {
      if (!seenIdsRef.current.has(n.id)) {
        seenIdsRef.current.add(n.id);
        appearedAt.set(n.id, now);
      }
    }
  }, [nodes, appearedAt]);

  useEffect(() => {
    if (!svgRef.current) return;
    const z = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 4])
      .filter((event) => {
        if (draggingIdRef.current) return false;
        const target = event.target as Element | null;
        return !target?.closest('g.node');
      })
      .on('zoom', (event) => setTransform({ k: event.transform.k, x: event.transform.x, y: event.transform.y }));
    zoomRef.current = z;
    select(svgRef.current).call(z);
    return () => {
      if (svgRef.current) select(svgRef.current).on('.zoom', null);
    };
  }, []);

  const toWorld = (clientX: number, clientY: number): { x: number; y: number } => {
    const rect = svgRef.current?.getBoundingClientRect();
    const t = transformRef.current;
    const sx = clientX - (rect?.left ?? 0);
    const sy = clientY - (rect?.top ?? 0);
    return { x: (sx - t.x) / t.k, y: (sy - t.y) / t.k };
  };

  const onNodePointerDown = (e: React.PointerEvent<SVGGElement>, n: SimNode) => {
    e.stopPropagation();
    (e.target as Element).setPointerCapture?.(e.pointerId);
    setDraggingId(n.id);
    const { x, y } = toWorld(e.clientX, e.clientY);
    pin(n.id, x, y);
  };

  const onNodePointerMove = (e: React.PointerEvent<SVGGElement>) => {
    if (!draggingIdRef.current) return;
    const { x, y } = toWorld(e.clientX, e.clientY);
    pin(draggingIdRef.current, x, y);
  };

  const onNodePointerUp = (e: React.PointerEvent<SVGGElement>, n: SimNode) => {
    if (!draggingIdRef.current) return;
    (e.target as Element).releasePointerCapture?.(e.pointerId);
    pin(n.id, null, null);
    setDraggingId(null);
  };

  const isFocused = (id: string): boolean => {
    if (selected) return selected.id === id || adjacency.get(selected.id)?.has(id) === true;
    if (hoveredId) return hoveredId === id || adjacency.get(hoveredId)?.has(id) === true;
    return true;
  };

  const isEdgeFocused = (e: SimLink): boolean => {
    const sid = typeof e.source === 'object' ? (e.source as SimNode).id : (e.source as string);
    const tid = typeof e.target === 'object' ? (e.target as SimNode).id : (e.target as string);
    if (selected) return sid === selected.id || tid === selected.id;
    if (hoveredId) return sid === hoveredId || tid === hoveredId;
    return true;
  };

  const dimAll = selected !== null || hoveredId !== null;
  const now = performance.now();

  const onBackgroundClick = () => {
    if (draggingIdRef.current) return;
    onSelect(null);
  };

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      style={{ width: '100%', height: '100%', display: 'block', cursor: draggingId ? 'grabbing' : 'grab' }}
      onClick={onBackgroundClick}
    >
      <title>Knowledge graph</title>
      <g transform={`translate(${transform.x},${transform.y}) scale(${transform.k})`}>
        {simLinks.map((e, i) => {
          const a = e.source as SimNode;
          const b = e.target as SimNode;
          if (!a || !b || a.x == null || b.x == null) return null;
          const focused = isEdgeFocused(e);
          const opacity = dimAll ? (focused ? 0.55 : 0.05) : 0.22;
          return (
            <line
              key={`${e.raw.from}-${e.raw.to}-${i}`}
              x1={a.x}
              y1={a.y ?? 0}
              x2={b.x}
              y2={b.y ?? 0}
              stroke={e.raw.plum ? 'var(--color-entity)' : 'var(--color-ink)'}
              strokeOpacity={opacity}
              strokeWidth={focused ? 1.4 : 1}
              strokeDasharray={e.raw.dashed ? '4 3' : ''}
              style={{ transition: 'stroke-opacity 200ms ease-out, stroke-width 200ms ease-out' }}
            />
          );
        })}
        {simNodes.map((n) => {
          const focused = isFocused(n.id);
          const r = radiusFor(n.kind);
          const fill = colorFor(n.kind);
          const isProvisional = n.status === 'provisional';
          const isSelected = selected?.id === n.id;
          const opacity = dimAll ? (focused ? 1 : 0.18) : 1;
          const age = now - (appearedAt.get(n.id) ?? now);
          const enter = Math.min(1, age / 600);

          return (
            <g
              key={n.id}
              className="node"
              transform={`translate(${n.x ?? 0},${n.y ?? 0})`}
              onMouseEnter={() => setHoveredId(n.id)}
              onMouseLeave={() => setHoveredId(null)}
              onPointerDown={(e) => onNodePointerDown(e, n)}
              onPointerMove={onNodePointerMove}
              onPointerUp={(e) => onNodePointerUp(e, n)}
              onClick={(e) => {
                e.stopPropagation();
                if (draggingIdRef.current === null) onSelect(n);
              }}
              style={{ cursor: draggingId === n.id ? 'grabbing' : 'pointer', opacity: opacity * enter }}
            >
              {isSelected && (
                <circle r={r + 6} fill="none" stroke="var(--color-accent-500)" strokeWidth={1.5} opacity={0.7} />
              )}
              <circle
                r={r * (0.4 + 0.6 * enter)}
                fill={fill}
                stroke={n.ownerless ? 'var(--color-action)' : '#FFFFFF'}
                strokeWidth={n.ownerless ? 1.5 : 1.2}
                strokeDasharray={isProvisional ? '3 2' : ''}
                opacity={n.status === 'superseded' ? 0.45 : 1}
                style={{ transition: 'r 250ms ease-out' }}
              />
              {(focused || transform.k > 0.7 || isSelected) && (
                <text
                  y={r + 12}
                  textAnchor="middle"
                  fontSize={11}
                  fill="var(--color-ink)"
                  fontFamily="var(--font-sans)"
                  style={{ pointerEvents: 'none', opacity: enter }}
                >
                  {trim(n.label)}
                </text>
              )}
            </g>
          );
        })}
      </g>
      <ResetOnFirstLoad zoomRef={zoomRef} svgRef={svgRef} />
    </svg>
  );
};

const ResetOnFirstLoad = ({
  zoomRef,
  svgRef,
}: {
  zoomRef: React.RefObject<ZoomBehavior<SVGSVGElement, unknown> | null>;
  svgRef: React.RefObject<SVGSVGElement | null>;
}) => {
  const armed = useRef(false);
  useEffect(() => {
    if (armed.current) return;
    armed.current = true;
    if (svgRef.current && zoomRef.current) {
      select(svgRef.current).call(zoomRef.current.transform, zoomIdentity);
    }
  }, [svgRef, zoomRef]);
  return null;
};
