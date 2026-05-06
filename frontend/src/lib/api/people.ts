import { apiGet } from './client';

export interface PersonListItemResponse {
  name: string;
  is_local_user: boolean;
  meeting_count: number;
  last_meeting_at: string | null;
  participant_ids: string[];
}

export interface PersonUtteranceItemResponse {
  id: string;
  meeting_id: string;
  meeting_title: string;
  t_start: number;
  text: string;
}

export const listPeople = () => apiGet<PersonListItemResponse[]>('/people');

export const listPersonUtterances = (name: string, limit = 6) =>
  apiGet<PersonUtteranceItemResponse[]>(
    `/people/utterances?name=${encodeURIComponent(name)}&limit=${limit}`,
  );
