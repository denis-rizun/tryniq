import { formatDuration, formatTimestamp, pad2 } from '@/lib/format';
import type { Meeting, MeetingListItem, PeopleMap, Utterance } from '@/lib/types';
import type {
  MeetingResponse,
  MeetingStatus,
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
  'finalizing',
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
    // TODO(api): backend list endpoint doesn't include participants yet
    participants: [],
    state: toState(m.status),
    duration: finalDuration,
    durationLive: liveDuration,
    startedAt: formatStartedAt(m.started_at),
    relativeStart: active ? 'live now' : formatRelative(m.started_at),
    // TODO(api): topics/decisions/questions counts not in backend yet (Phase 3)
    topPills: [],
    decCount: 0,
    qCount: 0,
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
  const base = name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  return base || `speaker_${idx + 1}`;
};

export const toMeeting = (t: TranscriptResponse, title: string): AdaptedTranscript => {
  const participantSlugById: Record<string, string> = {};
  const people: PeopleMap = {};
  t.participants.forEach((p, idx) => {
    const slug = slugifyName(p.name, idx);
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
    asrModel: 'whisper-large-v3',
    llmModel: 'claude-haiku-4.5',
    utterances,
    // TODO(api): graph extraction not implemented (Phase 3)
    decisions: [],
    actionItems: [],
    questions: [],
    topics: [],
    speakingTime: {},
    previousMeeting: { id: '', title: '', date: '', relatedTopics: [] },
    summary: '',
  };

  return { meeting, people, participantSlugById };
};
