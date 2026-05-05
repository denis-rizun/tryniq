import { config } from '@/lib/config';
import { ApiError, apiDelete, apiGet, apiPatch, apiPost } from './client';
import type {
  ChatScope,
  ChatSessionDetailResponse,
  ChatSessionResponse,
  ChatStreamEvent,
} from './types';

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
  const res = await fetch(`${config.apiBaseUrl}/chats/sessions/${sessionId}/messages`, {
    method: 'POST',
    cache: 'no-store',
    headers: { Accept: 'text/event-stream', 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new ApiError(res.status, `POST chat message failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = parseSseFrame(frame);
        if (event) onEvent(event);
        boundary = buffer.indexOf('\n\n');
      }
    }
  } finally {
    try {
      await reader.cancel();
    } catch {
      // already closed
    }
  }
};

const parseSseFrame = (frame: string): ChatStreamEvent | null => {
  const dataLines: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
  }
  if (dataLines.length === 0) return null;
  try {
    return JSON.parse(dataLines.join('\n')) as ChatStreamEvent;
  } catch {
    return null;
  }
};
