import { apiGet } from './client';

export interface MeetingSearchResult {
  id: string;
  type: 'meeting';
  title: string;
  summary: string | null;
  status: string;
  started_at: string;
  url: string;
}

export interface PersonSearchResult {
  id: string;
  type: 'person';
  name: string;
  is_local_user: boolean;
  meeting_count: number;
  url: string;
}

export interface UtteranceSearchResult {
  id: string;
  type: 'utterance';
  text: string;
  speaker_name: string | null;
  meeting_id: string;
  meeting_title: string;
  t_start: number;
  url: string;
}

export interface SearchResults {
  meetings: MeetingSearchResult[];
  people: PersonSearchResult[];
  utterances: UtteranceSearchResult[];
}

export interface SearchTotals {
  meetings: number;
  people: number;
  utterances: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResults;
  total: SearchTotals;
}

export const searchAll = (q: string, limit = 8) =>
  apiGet<SearchResponse>(`/search?q=${encodeURIComponent(q)}&limit=${limit}`);
