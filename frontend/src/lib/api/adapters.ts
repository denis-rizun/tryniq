import { formatDuration, formatTimestamp, pad2 } from '@/lib/format';
import type {
  ActionItem,
  ChatCitationView,
  ChatMessage as ChatMessageView,
  ChatSession as ChatSessionView,
  Decision,
  Meeting,
  MeetingListItem,
  OpenQuestion,
  PeopleMap,
  PreviousMeeting,
  Topic,
  Utterance,
} from '@/lib/types';
import type {
  ActionItemProjection,
  ChatCitation,
  ChatMessageResponse,
  ChatSessionDetailResponse,
  ChatSessionResponse,
  DecisionProjection,
  MeetingMetadataResponse,
  MeetingResponse,
  MeetingStatus,
  OpenQuestionProjection,
  RelatedMeetingProjection,
  TopicProjection,
  TranscriptResponse,
  UtteranceResponse,
} from './types';

const formatStartedAt = (iso: string): string => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })} · ${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())} UTC`;
};

const formatRelative = (iso: string): string => {
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return iso;
  const diffSec = Math.max(0, (Date.now() - d) / 1000);
  if (diffSec < 60) return 'just now';
  const m = Math.floor(diffSec / 60);
  if (m < 60) return `${m} min${m === 1 ? '' : 's'} ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} hr${h === 1 ? '' : 's'} ago`;
  const days = Math.floor(h / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
};

const PROCESSING_STATUSES: ReadonlySet<MeetingStatus> = new Set([
  'live',
  'uploading',
  'normalizing',
  'diarizing',
  'transcribing',
]);

export const isActive = (s: MeetingStatus | undefined): boolean =>
  s !== undefined && PROCESSING_STATUSES.has(s);

const toState = (s: MeetingStatus): 'live' | 'finalizing' | 'final' => {
  if (s === 'live') return 'live';
  if (s === 'final' || s === 'failed') return 'final';
  return 'finalizing';
};

export const toMeetingListItem = (m: MeetingResponse): MeetingListItem => {
  const active = isActive(m.status);
  const startedMs = new Date(m.started_at).getTime();
  const endedMs = m.ended_at ? new Date(m.ended_at).getTime() : null;
  const finalDuration = endedMs ? formatDuration((endedMs - startedMs) / 1000) : null;
  const liveDuration = active ? formatDuration((Date.now() - startedMs) / 1000) : null;

  return {
    id: m.id,
    title: m.title,
    participants: [],
    participantsCount: m.participants_count,
    state: toState(m.status),
    duration: finalDuration,
    durationLive: liveDuration,
    startedAt: formatStartedAt(m.started_at),
    relativeStart: active ? 'live now' : formatRelative(m.started_at),
    topPills: [],
    topicsCount: m.topics_count,
    decCount: m.decisions_count,
    qCount: m.open_questions_count,
  };
};

export const toUtterance = (
  u: UtteranceResponse,
  participantSlugById: Record<string, string>,
): Utterance => ({
  id: u.id,
  speaker: participantSlugById[u.participant_id] ?? u.participant_id,
  time: formatTimestamp(u.t_start),
  text: u.text,
  confidence: u.confidence ?? 1,
  lowWords: [],
  final: u.is_final,
});

export interface AdaptedTranscript {
  meeting: Meeting;
  people: PeopleMap;
  participantSlugById: Record<string, string>;
}

const AVATAR_COLORS = ['#A6B58F', '#C9A87A', '#B89AA5', '#9DA9B8', '#9C82A6', '#8FA6B5'];

const computeInitials = (name: string): string => {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

const slugifyName = (name: string, idx: number): string => {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '');
  return base || `speaker_${idx + 1}`;
};

export const toMeeting = (t: TranscriptResponse, title: string): AdaptedTranscript => {
  const participantSlugById: Record<string, string> = {};
  const people: PeopleMap = {};
  t.participants.forEach((p, idx) => {
    const base = slugifyName(p.name, idx);
    let slug = base;
    let suffix = 2;
    while (people[slug]) {
      slug = `${base}_${suffix}`;
      suffix += 1;
    }
    participantSlugById[p.id] = slug;
    const isPlaceholder = p.name === 'You';
    const displayName = p.is_local_user && !isPlaceholder ? `${p.name} (You)` : p.name;
    people[slug] = {
      id: p.id,
      name: displayName,
      initials: computeInitials(p.name),
      color: AVATAR_COLORS[idx % AVATAR_COLORS.length],
    };
  });

  const utterances = t.utterances.map((u) => toUtterance(u, participantSlugById));
  const participantSlugs = Object.keys(people);

  const active = isActive(t.status);
  const startedMs = new Date(t.started_at).getTime();
  const endedMs = t.ended_at ? new Date(t.ended_at).getTime() : null;

  const meeting: Meeting = {
    id: t.meeting_id,
    title,
    startedAt: formatStartedAt(t.started_at),
    duration: endedMs ? formatDuration((endedMs - startedMs) / 1000) : null,
    durationLive: active ? formatDuration((Date.now() - startedMs) / 1000) : null,
    participants: participantSlugs,
    state: toState(t.status),
    utterances,
    decisions: [],
    actionItems: [],
    questions: [],
    topics: [],
    speakingTime: {},
    previousMeetings: [],
    summary: '',
    metadataGeneratedAt: null,
  };

  return { meeting, people, participantSlugById };
};

const formatRelatedMeetingDate = (iso: string): string => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const formatTimeOrDash = (t: number | null): string => (t == null ? '—' : formatTimestamp(t));

const toDecision = (d: DecisionProjection): Decision => ({
  id: d.id,
  text: d.text,
  time: formatTimeOrDash(d.source_t_start),
  owner: d.owner_name,
  status: d.status,
});

const toActionItem = (a: ActionItemProjection): ActionItem => ({
  id: a.id,
  text: a.text,
  time: formatTimeOrDash(a.source_t_start),
  owner: a.owner_name,
  status: a.status === 'superseded' ? 'done' : 'open',
});

const toOpenQuestion = (q: OpenQuestionProjection): OpenQuestion => ({
  id: q.id,
  text: q.text,
  time: formatTimeOrDash(q.source_t_start),
  status:
    q.status === 'confirmed'
      ? 'answered'
      : q.status === 'superseded'
        ? 'partially-answered'
        : 'unanswered',
});

const toTopic = (t: TopicProjection): Topic => ({
  id: t.id,
  name: t.name,
  summary: t.summary ?? '',
  relatesPrevious: t.relates_previous,
});

const toPreviousMeeting = (r: RelatedMeetingProjection): PreviousMeeting => ({
  id: r.id,
  title: r.title,
  date: formatRelatedMeetingDate(r.started_at),
  relatedTopics: r.shared_topic_names,
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

export const toChatCitation = (c: ChatCitation): ChatCitationView => ({
  utteranceId: c.utterance_id,
  meetingId: c.meeting_id,
  meetingStartedAt: c.meeting_started_at,
  tStart: c.t_start,
  label: c.label,
});

export const toChatMessage = (m: ChatMessageResponse): ChatMessageView => ({
  id: m.id,
  role: m.role === 'user' ? 'user' : 'asst',
  text: m.text,
  model: m.model ?? undefined,
  sources: m.citations.length || undefined,
  latency: m.latency_ms != null ? `${(m.latency_ms / 1000).toFixed(1)}s` : undefined,
  citations: m.citations.map(toChatCitation),
});

export const toChatSessionList = (s: ChatSessionResponse): ChatSessionView => ({
  id: s.id,
  title: s.title,
  meetingId: s.meeting_id,
  scope: s.scope,
  isActive: false,
  relTime: s.last_message_at ? formatRelative(s.last_message_at) : formatRelative(s.updated_at),
  messages: [],
});

export const toChatSessionDetail = (s: ChatSessionDetailResponse): ChatSessionView => ({
  id: s.id,
  title: s.title,
  meetingId: s.meeting_id,
  scope: s.scope,
  isActive: false,
  relTime: formatRelative(s.updated_at),
  messages: s.messages.map(toChatMessage),
});
