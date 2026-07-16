import { apiGet } from './client';
import type { GraphNodeStatusBackend } from './graph';

export interface DecisionProjection {
  id: string;
  text: string;
  status: GraphNodeStatusBackend;
  owner_name: string | null;
  source_t_start: number | null;
  source_utterance_id: string | null;
  topic_ids: string[];
}

export interface ActionItemProjection extends DecisionProjection {
  due_date: string | null;
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

export const getMeetingMetadata = (id: string) =>
  apiGet<MeetingMetadataResponse>(`/meetings/${id}/metadata`);
