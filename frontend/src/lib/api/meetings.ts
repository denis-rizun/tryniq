import { apiGet, apiPatch, apiUpload } from './client';

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

export interface UploadResponse {
  meeting_id: string;
}

export const uploadRecording = async (file: File, title?: string): Promise<UploadResponse> => {
  const form = new FormData();
  form.append('file', file);
  if (title) form.append('title', title);

  return apiUpload<UploadResponse>('/meetings/upload', form);
};

export const listMeetings = () => apiGet<MeetingResponse[]>('/meetings');

export const getTranscript = (id: string) =>
  apiGet<TranscriptResponse>(`/meetings/${id}/transcript`);

export const renameMeeting = (id: string, title: string) =>
  apiPatch<MeetingResponse>(`/meetings/${id}`, { title });
