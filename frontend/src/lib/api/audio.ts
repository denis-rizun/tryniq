import { apiGet, apiGetBlob, type BlobResponse } from './client';

export interface AudioTrack {
  stream_id: string;
  participant_id: string;
  participant_name: string;
  is_local_user: boolean;
  part: number;
  object_key: string;
  filename: string;
}

export const listAudioTracks = (meetingId: string) =>
  apiGet<AudioTrack[]>(`/meetings/${meetingId}/audio`);

export const downloadAudioTrack = (
  meetingId: string,
  streamId: string,
  part: number,
): Promise<BlobResponse> =>
  apiGetBlob(`/meetings/${meetingId}/audio/${streamId}?part=${part}`);
