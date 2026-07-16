import { apiDelete, apiGet, apiPatch, apiPost, apiStream } from './client';

export type ChatScope = 'meeting' | 'all';
export type ChatRole = 'user' | 'assistant';

export interface ChatCitation {
  utterance_id: string;
  meeting_id: string;
  meeting_title: string | null;
  meeting_started_at: string | null;
  t_start: number;
  t_end: number;
  speaker: string | null;
  text: string;
  label: string;
}

export interface ChatMessageResponse {
  id: string;
  session_id: string;
  role: ChatRole;
  text: string;
  citations: ChatCitation[];
  model: string | null;
  latency_ms: number | null;
  created_at: string;
}

export interface ChatSessionResponse {
  id: string;
  title: string;
  scope: ChatScope;
  meeting_id: string | null;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
  last_message_preview: string | null;
}

export interface ChatSessionDetailResponse {
  id: string;
  title: string;
  scope: ChatScope;
  meeting_id: string | null;
  created_at: string;
  updated_at: string;
  messages: ChatMessageResponse[];
}

export type ChatStreamEvent =
  | { kind: 'message_started'; user_message: ChatMessageResponse; assistant_message_id: string }
  | { kind: 'token'; delta: string }
  | { kind: 'message_completed'; message: ChatMessageResponse }
  | { kind: 'error'; detail: string };

export interface CreateChatSessionInput {
  scope: ChatScope;
  meeting_id?: string | null;
  title?: string | null;
}

export interface ListChatSessionsParams {
  scope?: ChatScope;
  meetingId?: string;
}

export const listChatSessions = ({
  scope,
  meetingId,
}: ListChatSessionsParams = {}): Promise<ChatSessionResponse[]> => {
  const search = new URLSearchParams();
  if (scope) search.set('scope', scope);
  if (meetingId) search.set('meeting_id', meetingId);
  const qs = search.toString();
  return apiGet<ChatSessionResponse[]>(`/chats/sessions${qs ? `?${qs}` : ''}`);
};

export const getChatSession = (id: string) =>
  apiGet<ChatSessionDetailResponse>(`/chats/sessions/${id}`);

export const createChatSession = (input: CreateChatSessionInput) =>
  apiPost<ChatSessionResponse>('/chats/sessions', input);

export const renameChatSession = (id: string, title: string) =>
  apiPatch<ChatSessionResponse>(`/chats/sessions/${id}`, { title });

export const deleteChatSession = (id: string) => apiDelete(`/chats/sessions/${id}`);

export interface StreamChatMessageHandlers {
  onEvent: (event: ChatStreamEvent) => void;
  signal?: AbortSignal;
}

export const streamChatMessage = async (
  sessionId: string,
  text: string,
  { onEvent, signal }: StreamChatMessageHandlers,
): Promise<void> => {
  await apiStream<ChatStreamEvent>(
    `/chats/sessions/${sessionId}/messages`,
    { text },
    { onEvent, signal },
  );
};
