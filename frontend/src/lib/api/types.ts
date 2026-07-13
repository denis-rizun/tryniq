export type MeetingStatus =
  | 'live'
  | 'uploading'
  | 'normalizing'
  | 'diarizing'
  | 'transcribing'
  | 'finalizing'
  | 'final'
  | 'failed';

export interface MeetingResponse {
  id: string;
  title: string;
  meet_url: string;
  meet_code: string;
  room_id: string;
  status: MeetingStatus;
  started_at: string;
  ended_at: string | null;
  summary: string | null;
  metadata_generated_at: string | null;
  participants_count: number;
  decisions_count: number;
  open_questions_count: number;
  topics_count: number;
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
  event:
    | 'started'
    | 'ended'
    | 'uploading'
    | 'normalizing'
    | 'diarizing'
    | 'transcribing'
    | 'finalizing'
    | 'final'
    | 'failed'
    | 'metadata_ready';
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

export type ChatScope = 'meeting' | 'all';
export type ChatRole = 'user' | 'assistant';

export interface ChatCitation {
  utterance_id: string;
  meeting_id: string;
  meeting_title: string | null;
  meeting_started_at: string | null;
  t_start: number;
  t_end: number;
  speaker: string | null;
  text: string;
  label: string;
}

export interface ChatMessageResponse {
  id: string;
  session_id: string;
  role: ChatRole;
  text: string;
  citations: ChatCitation[];
  model: string | null;
  latency_ms: number | null;
  created_at: string;
}

export interface ChatSessionResponse {
  id: string;
  title: string;
  scope: ChatScope;
  meeting_id: string | null;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
  last_message_preview: string | null;
}

export interface ChatSessionDetailResponse {
  id: string;
  title: string;
  scope: ChatScope;
  meeting_id: string | null;
  created_at: string;
  updated_at: string;
  messages: ChatMessageResponse[];
}

export interface ChatStreamMessageStarted {
  kind: 'message_started';
  user_message: ChatMessageResponse;
  assistant_message_id: string;
}

export interface ChatStreamToken {
  kind: 'token';
  delta: string;
}

export interface ChatStreamCompleted {
  kind: 'message_completed';
  message: ChatMessageResponse;
}

export interface ChatStreamError {
  kind: 'error';
  detail: string;
}

export type ChatStreamEvent =
  | ChatStreamMessageStarted
  | ChatStreamToken
  | ChatStreamCompleted
  | ChatStreamError;

export interface DecisionProjection {
  id: string;
  text: string;
  status: GraphNodeStatusBackend;
  owner_name: string | null;
  source_t_start: number | null;
  source_utterance_id: string | null;
  topic_ids: string[];
}

export interface ActionItemProjection {
  id: string;
  text: string;
  status: GraphNodeStatusBackend;
  due_date: string | null;
  owner_name: string | null;
  source_t_start: number | null;
  source_utterance_id: string | null;
  topic_ids: string[];
}

export interface OpenQuestionProjection {
  id: string;
  text: string;
  status: GraphNodeStatusBackend;
  source_t_start: number | null;
  source_utterance_id: string | null;
  topic_ids: string[];
}

export interface TopicProjection {
  id: string;
  name: string;
  summary: string | null;
  relates_previous: boolean;
}

export interface RelatedMeetingProjection {
  id: string;
  title: string;
  started_at: string;
  shared_topic_names: string[];
}

export interface MeetingMetadataResponse {
  meeting_id: string;
  summary: string | null;
  metadata_generated_at: string | null;
  decisions: DecisionProjection[];
  action_items: ActionItemProjection[];
  open_questions: OpenQuestionProjection[];
  topics: TopicProjection[];
  related_meetings: RelatedMeetingProjection[];
}
