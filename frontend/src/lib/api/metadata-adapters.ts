import { formatTimestamp } from '@/lib/format';
import type {
  ActionItem,
  Decision,
  Meeting,
  OpenQuestion,
  PreviousMeeting,
  Topic,
} from '@/lib/types';
import type {
  ActionItemProjection,
  DecisionProjection,
  MeetingMetadataResponse,
  OpenQuestionProjection,
  RelatedMeetingProjection,
  TopicProjection,
} from './metadata';

const formatTimeOrDash = (time: number | null): string =>
  time == null ? '—' : formatTimestamp(time);
const toDecision = (item: DecisionProjection): Decision => ({
  id: item.id,
  text: item.text,
  time: formatTimeOrDash(item.source_t_start),
  owner: item.owner_name,
  status: item.status,
});
const toActionItem = (item: ActionItemProjection): ActionItem => ({
  id: item.id,
  text: item.text,
  time: formatTimeOrDash(item.source_t_start),
  owner: item.owner_name,
  status: item.status === 'superseded' ? 'done' : 'open',
});
const toOpenQuestion = (item: OpenQuestionProjection): OpenQuestion => ({
  id: item.id,
  text: item.text,
  time: formatTimeOrDash(item.source_t_start),
  status:
    item.status === 'confirmed'
      ? 'answered'
      : item.status === 'superseded'
        ? 'partially-answered'
        : 'unanswered',
});
const toTopic = (item: TopicProjection): Topic => ({
  id: item.id,
  name: item.name,
  summary: item.summary ?? '',
  relatesPrevious: item.relates_previous,
});
const toPreviousMeeting = (item: RelatedMeetingProjection): PreviousMeeting => ({
  id: item.id,
  title: item.title,
  date: new Date(item.started_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }),
  relatedTopics: item.shared_topic_names,
});

export const applyMeetingMetadata = (
  meeting: Meeting,
  metadata: MeetingMetadataResponse,
): Meeting => ({
  ...meeting,
  summary: metadata.summary ?? '',
  metadataGeneratedAt: metadata.metadata_generated_at,
  decisions: metadata.decisions.map(toDecision),
  actionItems: metadata.action_items.map(toActionItem),
  questions: metadata.open_questions.map(toOpenQuestion),
  topics: metadata.topics.map(toTopic),
  previousMeetings: metadata.related_meetings.map(toPreviousMeeting),
});
