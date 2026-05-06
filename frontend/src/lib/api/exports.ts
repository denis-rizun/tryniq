import { apiGetBlob, type BlobResponse } from './client';

export const fetchMeetingExport = async (
  meetingId: string,
  sections: string[],
): Promise<BlobResponse> => {
  const query = sections.length ? `?include=${encodeURIComponent(sections.join(','))}` : '';
  return apiGetBlob(`/meetings/${meetingId}/export${query}`);
};
