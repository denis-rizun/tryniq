import { config } from '@/lib/config';
import { ApiError, apiGet, apiPatch } from './client';
import type {
  GraphResponse,
  MeetingMetadataResponse,
  MeetingResponse,
  TranscriptResponse,
} from './types';

export interface UploadResponse {
  meeting_id: string;
}

export const uploadRecording = async (file: File, title?: string): Promise<UploadResponse> => {
  const form = new FormData();
  form.append('file', file);
  if (title) form.append('title', title);

  const res = await fetch(`${config.apiBaseUrl}/meetings/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new ApiError(res.status, `upload failed: ${res.status} ${detail}`);
  }
  return (await res.json()) as UploadResponse;
};

export const listMeetings = () => apiGet<MeetingResponse[]>('/meetings');

export const getTranscript = (id: string) =>
  apiGet<TranscriptResponse>(`/meetings/${id}/transcript`);

export const renameMeeting = (id: string, title: string) =>
  apiPatch<MeetingResponse>(`/meetings/${id}`, { title });

export const getMeetingGraph = (id: string) => apiGet<GraphResponse>(`/meetings/${id}/graph`);

export const getMeetingMetadata = (id: string) =>
  apiGet<MeetingMetadataResponse>(`/meetings/${id}/metadata`);
