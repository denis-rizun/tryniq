'use client';

import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from 'd3-force';
import { useEffect, useRef, useState } from 'react';
import type { GraphEdge, GraphNode } from '@/components/meeting/graph/graph-data';

export interface SimNode extends SimulationNodeDatum, GraphNode {}
export interface SimLink extends SimulationLinkDatum<SimNode> {
  raw: GraphEdge;
}

export interface SimulationState {
  nodes: SimNode[];
  links: SimLink[];
  tick: number;
  pin: (id: string, x: number | null, y: number | null) => void;
  reheat: () => void;
  tidy: (positions: Map<string, { x: number; y: number }>) => void;
}

export const useGraphSimulation = (
  graphNodes: GraphNode[],
  graphEdges: GraphEdge[],
  width: number,
  height: number,
): SimulationState => {
  const nodesRef = useRef<SimNode[]>([]);
  const linksRef = useRef<SimLink[]>([]);
  const simRef = useRef<Simulation<SimNode, SimLink> | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const byId = new Map(nodesRef.current.map((n) => [n.id, n]));
    nodesRef.current = graphNodes.map((g) => {
      const existing = byId.get(g.id);
      if (existing) {
        Object.assign(existing, g);
        return existing;
      }
      return { ...g, x: width / 2 + (Math.random() - 0.5) * 80, y: height / 2 + (Math.random() - 0.5) * 80 };
    });

    linksRef.current = graphEdges.map((e) => ({
      source: e.from,
      target: e.to,
      raw: e,
    }));

    if (!simRef.current) {
      simRef.current = forceSimulation<SimNode, SimLink>(nodesRef.current)
        .force('link', forceLink<SimNode, SimLink>(linksRef.current).id((d) => d.id).distance(80).strength(0.6))
        .force('charge', forceManyBody().strength(-220))
        .force('center', forceCenter(width / 2, height / 2))
        .force('collide', forceCollide<SimNode>().radius((n) => radiusFor(n.kind) + 6))
        .force('x', forceX(width / 2).strength(0.04))
        .force('y', forceY(height / 2).strength(0.04))
        .alphaDecay(0.035)
        .on('tick', () => setTick((t) => t + 1));
    } else {
      simRef.current.nodes(nodesRef.current);
      const linkForce = simRef.current.force<ReturnType<typeof forceLink<SimNode, SimLink>>>('link');
      linkForce?.links(linksRef.current);
      simRef.current.force('center', forceCenter(width / 2, height / 2));
      simRef.current.alpha(0.7).restart();
    }
  }, [graphNodes, graphEdges, width, height]);

  useEffect(() => {
    return () => {
      simRef.current?.stop();
      simRef.current = null;
    };
  }, []);

  const pin = (id: string, x: number | null, y: number | null) => {
    const node = nodesRef.current.find((n) => n.id === id);
    if (!node) return;
    node.fx = x ?? null;
    node.fy = y ?? null;
    simRef.current?.alphaTarget(x === null ? 0 : 0.3).restart();
  };

  const reheat = () => simRef.current?.alpha(0.7).restart();

  const tidy = (positions: Map<string, { x: number; y: number }>) => {
    for (const node of nodesRef.current) {
      const target = positions.get(node.id);
      if (!target) continue;
      node.fx = target.x;
      node.fy = target.y;
    }
    simRef.current?.alpha(0.9).alphaTarget(0).restart();
    setTimeout(() => {
      for (const node of nodesRef.current) {
        if (positions.has(node.id)) {
          node.fx = null;
          node.fy = null;
        }
      }
    }, 700);
  };

  return { nodes: nodesRef.current, links: linksRef.current, tick, pin, reheat, tidy };
};

const RADIUS_BY_KIND: Record<GraphNode['kind'], number> = {
  meeting: 12,
  topic: 10,
  decision: 9,
  action: 9,
  question: 9,
  person: 8,
  entity: 6,
};

export const radiusFor = (kind: GraphNode['kind']): number => RADIUS_BY_KIND[kind];
