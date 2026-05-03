'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo } from 'react';
import { adaptGraph } from '@/lib/api/graph-adapter';
import { subscribeMeetingEvents } from '@/lib/api/events';
import { getMeetingGraph } from '@/lib/api/meetings';
import type { GraphPatchEvent, GraphResponse, LiveEvent } from '@/lib/api/types';
import type { GraphEdge, GraphNode } from '@/components/meeting/graph/graph-data';

const graphKey = (meetingId: string) => ['meeting-graph', meetingId] as const;

const applyPatch = (current: GraphResponse | undefined, patch: GraphPatchEvent): GraphResponse => {
  const base: GraphResponse = current ?? { nodes: [], edges: [] };
  const updatedById = new Map(patch.updated_nodes.map((n) => [n.id, n]));
  const nodes = base.nodes.map((n) => updatedById.get(n.id) ?? n);
  const knownIds = new Set(nodes.map((n) => n.id));
  for (const n of patch.added_nodes) {
    if (!knownIds.has(n.id)) nodes.push(n);
  }
  const edgeIds = new Set(base.edges.map((e) => e.id));
  const edges = [...base.edges];
  for (const e of patch.added_edges) {
    if (!edgeIds.has(e.id)) edges.push(e);
  }
  return { nodes, edges };
};

export interface UseMeetingGraphResult {
  nodes: GraphNode[];
  edges: GraphEdge[];
  isLoading: boolean;
  isError: boolean;
}

export const useMeetingGraph = (meetingId: string, enabled: boolean = true): UseMeetingGraphResult => {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: graphKey(meetingId),
    queryFn: () => getMeetingGraph(meetingId),
    enabled: enabled && Boolean(meetingId),
  });

  useEffect(() => {
    if (!enabled || !meetingId) return;
    const handle = (event: LiveEvent) => {
      if (event.kind !== 'graph_patch') return;
      queryClient.setQueryData<GraphResponse>(graphKey(meetingId), (prev) => applyPatch(prev, event));
    };
    const unsubscribe = subscribeMeetingEvents(meetingId, { onEvent: handle });
    return () => unsubscribe();
  }, [meetingId, enabled, queryClient]);

  const adapted = useMemo(() => (query.data ? adaptGraph(query.data) : { nodes: [], edges: [] }), [query.data]);

  return {
    nodes: adapted.nodes,
    edges: adapted.edges,
    isLoading: query.isLoading,
    isError: query.isError,
  };
};
