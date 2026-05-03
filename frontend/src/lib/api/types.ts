export type MeetingStatus = 'live' | 'finalizing' | 'final' | 'failed';

export interface MeetingResponse {
  id: string;
  title: string;
  meet_url: string;
  meet_code: string;
  room_id: string;
  status: MeetingStatus;
  started_at: string;
  ended_at: string | null;
}

export interface ParticipantResponse {
  id: string;
  stream_id: string;
  name: string;
  is_local_user: boolean;
}

export interface UtteranceResponse {
  id: string;
  participant_id: string;
  stream_id: string;
  t_start: number;
  t_end: number;
  text: string;
  confidence: number | null;
  model: string | null;
  word_timings: unknown[] | null;
  is_final: boolean;
}

export interface TranscriptResponse {
  meeting_id: string;
  status: MeetingStatus;
  participants: ParticipantResponse[];
  utterances: UtteranceResponse[];
  started_at: string;
  ended_at: string | null;
}

export interface MeetingLifecycleEvent {
  kind: 'meeting_lifecycle';
  meeting_id: string;
  event: 'started' | 'ended' | 'finalizing' | 'final';
  timestamp: string;
}

export interface PartialTranscriptEvent {
  kind: 'partial_transcript';
  meeting_id: string;
  stream_id: string;
  participant_id: string | null;
  text: string;
  timestamp: string;
}

export interface TranscriptSegmentEvent {
  kind: 'transcript_segment';
  meeting_id: string;
  stream_id: string;
  participant_id: string | null;
  utterance_id: string;
  text: string;
  t_start: number;
  t_end: number;
  is_final: boolean;
  timestamp: string;
}

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

export interface GraphNodeRead {
  id: string;
  meeting_id: string;
  type: GraphNodeType;
  fields: Record<string, unknown>;
  status: GraphNodeStatusBackend;
  created_at: string;
}

export interface GraphEdgeRead {
  id: string;
  meeting_id: string;
  type: GraphEdgeType;
  from_id: string;
  to_id: string;
  created_at: string;
}

export interface GraphResponse {
  nodes: GraphNodeRead[];
  edges: GraphEdgeRead[];
}

export interface GraphPatchEvent {
  kind: 'graph_patch';
  meeting_id: string;
  added_nodes: GraphNodeRead[];
  added_edges: GraphEdgeRead[];
  updated_nodes: GraphNodeRead[];
  timestamp: string;
}

export type LiveEvent =
  | MeetingLifecycleEvent
  | PartialTranscriptEvent
  | TranscriptSegmentEvent
  | GraphPatchEvent;

export interface PingEvent {
  kind: 'ping';
}

export type GlobalEvent = MeetingLifecycleEvent | PingEvent;
