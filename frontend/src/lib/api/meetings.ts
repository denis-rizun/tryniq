import { apiGet, apiPatch } from './client';
import type { MeetingResponse, TranscriptResponse } from './types';

export const listMeetings = () => apiGet<MeetingResponse[]>('/meetings');

export const getTranscript = (id: string) =>
  apiGet<TranscriptResponse>(`/meetings/${id}/transcript`);

export const renameMeeting = (id: string, title: string) =>
  apiPatch<MeetingResponse>(`/meetings/${id}`, { title });
