import { formatRelative } from '@/lib/format';
import type {
  ChatCitationView,
  ChatMessage as ChatMessageView,
  ChatSession as ChatSessionView,
} from '@/lib/types';
import type {
  ChatCitation,
  ChatMessageResponse,
  ChatSessionDetailResponse,
  ChatSessionResponse,
} from './chat';

export const toChatCitation = (citation: ChatCitation): ChatCitationView => ({
  utteranceId: citation.utterance_id,
  meetingId: citation.meeting_id,
  meetingStartedAt: citation.meeting_started_at,
  tStart: citation.t_start,
  label: citation.label,
});
export const toChatMessage = (message: ChatMessageResponse): ChatMessageView => ({
  id: message.id,
  role: message.role === 'user' ? 'user' : 'asst',
  text: message.text,
  model: message.model ?? undefined,
  sources: message.citations.length || undefined,
  latency: message.latency_ms != null ? `${(message.latency_ms / 1000).toFixed(1)}s` : undefined,
  citations: message.citations.map(toChatCitation),
});
export const toChatSessionList = (session: ChatSessionResponse): ChatSessionView => ({
  id: session.id,
  title: session.title,
  meetingId: session.meeting_id,
  scope: session.scope,
  isActive: false,
  relTime: formatRelative(session.last_message_at ?? session.updated_at),
  messages: [],
});
export const toChatSessionDetail = (session: ChatSessionDetailResponse): ChatSessionView => ({
  id: session.id,
  title: session.title,
  meetingId: session.meeting_id,
  scope: session.scope,
  isActive: false,
  relTime: formatRelative(session.updated_at),
  messages: session.messages.map(toChatMessage),
});
