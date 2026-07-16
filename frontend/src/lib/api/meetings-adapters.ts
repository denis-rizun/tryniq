import {
  colorForId,
  formatDuration,
  formatRelative,
  formatTimestamp,
  initialsOf,
  pad2,
} from '@/lib/format';
import type { Meeting, MeetingListItem, PeopleMap, Utterance } from '@/lib/types';
import type {
  MeetingResponse,
  MeetingStatus,
  TranscriptResponse,
  UtteranceResponse,
} from './meetings';

const PROCESSING_STATUSES: ReadonlySet<MeetingStatus> = new Set([
  'live',
  'uploading',
  'normalizing',
  'diarizing',
  'transcribing',
]);

export const formatStartedAt = (iso: string): string => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${date.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} · ${pad2(date.getUTCHours())}:${pad2(date.getUTCMinutes())} UTC`;
};

export const isActive = (status: MeetingStatus | undefined): boolean =>
  status !== undefined && PROCESSING_STATUSES.has(status);

export const toMeetingState = (status: MeetingStatus): 'live' | 'finalizing' | 'final' => {
  if (status === 'live') return 'live';
  return status === 'final' || status === 'failed' ? 'final' : 'finalizing';
};

export const toMeetingListItem = (meeting: MeetingResponse): MeetingListItem => {
  const active = isActive(meeting.status);
  const startedMs = new Date(meeting.started_at).getTime();
  const endedMs = meeting.ended_at ? new Date(meeting.ended_at).getTime() : null;
  return {
    id: meeting.id,
    title: meeting.title,
    participantsCount: meeting.participants_count,
    state: toMeetingState(meeting.status),
    duration: endedMs ? formatDuration((endedMs - startedMs) / 1000) : null,
    durationLive: active ? formatDuration((Date.now() - startedMs) / 1000) : null,
    startedAt: formatStartedAt(meeting.started_at),
    relativeStart: active ? 'live now' : formatRelative(meeting.started_at),
    topicsCount: meeting.topics_count,
    decCount: meeting.decisions_count,
    qCount: meeting.open_questions_count,
  };
};

export const toUtterance = (
  utterance: UtteranceResponse,
  participantSlugById: Record<string, string>,
): Utterance => ({
  id: utterance.id,
  speaker: participantSlugById[utterance.participant_id] ?? utterance.participant_id,
  time: formatTimestamp(utterance.t_start),
  text: utterance.text,
  confidence: utterance.confidence ?? 1,
  lowWords: [],
  final: utterance.is_final,
});

export interface AdaptedTranscript {
  meeting: Meeting;
  people: PeopleMap;
  participantSlugById: Record<string, string>;
}

export const slugifyName = (name: string, index: number): string => {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '');
  return base || `speaker_${index + 1}`;
};

export const toMeeting = (transcript: TranscriptResponse, title: string): AdaptedTranscript => {
  const participantSlugById: Record<string, string> = {};
  const people: PeopleMap = {};
  transcript.participants.forEach((participant, index) => {
    const base = slugifyName(participant.name, index);
    let slug = base;
    for (let suffix = 2; people[slug]; suffix++) slug = `${base}_${suffix}`;
    participantSlugById[participant.id] = slug;
    people[slug] = {
      id: participant.id,
      name:
        participant.is_local_user && participant.name !== 'You'
          ? `${participant.name} (You)`
          : participant.name,
      initials: initialsOf(participant.name),
      color: colorForId(`${participant.id}-${index}`),
    };
  });
  const startedMs = new Date(transcript.started_at).getTime();
  const endedMs = transcript.ended_at ? new Date(transcript.ended_at).getTime() : null;
  return {
    participantSlugById,
    people,
    meeting: {
      id: transcript.meeting_id,
      title,
      startedAt: formatStartedAt(transcript.started_at),
      duration: endedMs ? formatDuration((endedMs - startedMs) / 1000) : null,
      durationLive: isActive(transcript.status)
        ? formatDuration((Date.now() - startedMs) / 1000)
        : null,
      participants: Object.keys(people),
      state: toMeetingState(transcript.status),
      utterances: transcript.utterances.map((utterance) =>
        toUtterance(utterance, participantSlugById),
      ),
      decisions: [],
      actionItems: [],
      questions: [],
      topics: [],
      speakingTime: {},
      previousMeetings: [],
      summary: '',
      metadataGeneratedAt: null,
    },
  };
};
