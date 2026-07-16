import { apiGet } from './client';

export type GraphNodeType =
  | 'Meeting'
  | 'Person'
  | 'Topic'
  | 'Decision'
  | 'ActionItem'
  | 'OpenQuestion'
  | 'Entity'
  | 'Utterance';

export type GraphNodeStatusBackend = 'provisional' | 'confirmed' | 'superseded';

export type GraphEdgeType =
  | 'PARTICIPATED_IN'
  | 'DISCUSSED_IN'
  | 'MADE_DECISION'
  | 'ASSIGNED_TO'
  | 'BLOCKS'
  | 'ABOUT_TOPIC'
  | 'MENTIONS'
  | 'SOURCE'
  | 'RELATES_TO';

export interface GraphNodeResponse {
  id: string;
  meeting_id: string;
  type: GraphNodeType;
  fields: Record<string, unknown>;
  status: GraphNodeStatusBackend;
  created_at: string;
}

export interface GraphEdgeResponse {
  id: string;
  meeting_id: string;
  type: GraphEdgeType;
  from_id: string;
  to_id: string;
  created_at: string;
}

export interface GraphResponse {
  nodes: GraphNodeResponse[];
  edges: GraphEdgeResponse[];
}

export interface GraphPatchEvent {
  kind: 'graph_patch';
  meeting_id: string;
  added_nodes: GraphNodeResponse[];
  added_edges: GraphEdgeResponse[];
  updated_nodes: GraphNodeResponse[];
  timestamp: string;
}

export const getMeetingGraph = (id: string) => apiGet<GraphResponse>(`/meetings/${id}/graph`);
