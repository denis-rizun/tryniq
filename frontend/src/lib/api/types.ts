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

export type LiveEvent =
  | MeetingLifecycleEvent
  | PartialTranscriptEvent
  | TranscriptSegmentEvent;

export interface PingEvent {
  kind: 'ping';
}

export type GlobalEvent = MeetingLifecycleEvent | PingEvent;
