export type PersonId = string;

export interface Person {
  id: PersonId;
  name: string;
  initials: string;
  color: string;
}

export type PeopleMap = Record<string, Person>;

export interface Utterance {
  id: string;
  speaker: string;
  time: string;
  text: string;
  confidence: number;
  lowWords: number[];
  final: boolean;
}

export type NodeStatus = 'provisional' | 'confirmed' | 'superseded';

export interface Decision {
  id: string;
  text: string;
  time: string;
  owner: string | null;
  status: NodeStatus;
}

export interface ActionItem {
  id: string;
  text: string;
  time: string;
  owner: string | null;
  status: 'open' | 'done';
}

export interface OpenQuestion {
  id: string;
  text: string;
  time: string;
  status: 'unanswered' | 'partially-answered' | 'answered';
  stale?: boolean;
}

export interface Topic {
  id: string;
  name: string;
  summary: string;
  relatesPrevious?: boolean;
}

export interface PreviousMeeting {
  id: string;
  title: string;
  date: string;
  relatedTopics: string[];
}

export interface Meeting {
  id: string;
  title: string;
  startedAt: string;
  duration?: string | null;
  durationLive?: string | null;
  participants: string[];
  state: 'live' | 'finalizing' | 'final';
  utterances: Utterance[];
  decisions: Decision[];
  actionItems: ActionItem[];
  questions: OpenQuestion[];
  topics: Topic[];
  speakingTime: Record<string, number>;
  previousMeetings: PreviousMeeting[];
  summary: string;
  metadataGeneratedAt: string | null;
}

export interface MeetingListItem {
  id: string;
  title: string;
  participants: string[];
  state: 'live' | 'finalizing' | 'final';
  duration?: string | null;
  durationLive?: string | null;
  startedAt: string;
  relativeStart: string;
  topPills: string[];
  decCount: number;
  qCount: number;
}

export interface ChatCitationView {
  utteranceId: string;
  meetingId: string;
  meetingStartedAt: string | null;
  tStart: number;
  label: string;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'asst';
  text: string;
  model?: string;
  sources?: number;
  latency?: string;
  citations?: ChatCitationView[];
  pending?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  meetingId: string | null;
  scope: 'meeting' | 'all';
  isActive: boolean;
  relTime: string;
  messages: ChatMessage[];
}
