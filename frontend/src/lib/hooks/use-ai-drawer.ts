'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Scope } from '@/components/chat/scope-toggle';
import type { ChatScope } from '@/lib/api/chat';
import { createChatSession, getChatSession, listChatSessions } from '@/lib/api/chat';
import { toChatSessionDetail, toChatSessionList } from '@/lib/api/chat-adapters';
import { useChatStream } from '@/lib/hooks/use-chat-stream';
import { useUIStore } from '@/lib/store';
import type { ChatSession } from '@/lib/types';

type Filter = 'meeting' | 'all' | 'all-scope';

const sessionsKey = ['chat', 'sessions'] as const;
const sessionKey = (id: string) => ['chat', 'session', id] as const;

interface UseAIDrawerOptions {
  meetingId?: string | null;
  meetingFinal?: boolean;
}

export const useAIDrawer = (
  open: boolean,
  defaultFilter: Filter,
  defaultScope: Scope,
  { meetingId = null, meetingFinal = true }: UseAIDrawerOptions = {},
) => {
  const queryClient = useQueryClient();
  const { activeSessionId, setActiveSessionId } = useUIStore();
  const [filter, setFilter] = useState<Filter>(defaultFilter);
  const [draftScope, setDraftScope] = useState<Scope>(defaultScope);
  const [draft, setDraft] = useState('');
  const msgsRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (open) {
      setFilter(defaultFilter);
      setDraftScope(defaultScope);
    }
  }, [defaultFilter, defaultScope, open]);

  const sessionsQuery = useQuery({
    queryKey: sessionsKey,
    queryFn: () => listChatSessions(),
    enabled: open,
  });
  const sessionQuery = useQuery({
    queryKey: activeSessionId ? sessionKey(activeSessionId) : ['chat', 'session', 'none'],
    queryFn: () => (activeSessionId ? getChatSession(activeSessionId) : Promise.resolve(null)),
    enabled: open && Boolean(activeSessionId),
  });
  const sessions: ChatSession[] = useMemo(
    () => (sessionsQuery.data ?? []).map(toChatSessionList),
    [sessionsQuery.data],
  );
  const activeBase = useMemo(() => {
    if (sessionQuery.data) return toChatSessionDetail(sessionQuery.data);
    return sessions.find((session) => session.id === activeSessionId) ?? null;
  }, [activeSessionId, sessionQuery.data, sessions]);
  const scope: Scope = activeBase?.scope ?? draftScope;
  const ensureSession = useCallback(async () => {
    if (activeBase?.scope === scope) return activeBase.id;
    const chatScope: ChatScope = scope;
    const session = await createChatSession({
      scope: chatScope,
      meeting_id: chatScope === 'meeting' ? meetingId : null,
    });
    setActiveSessionId(session.id);
    await queryClient.invalidateQueries({ queryKey: sessionsKey });
    return session.id;
  }, [activeBase, meetingId, queryClient, scope, setActiveSessionId]);
  const {
    active,
    cancel,
    send: streamMessage,
    streaming,
  } = useChatStream({ activeBase, ensureSession });
  const filteredSessions = useMemo(
    () =>
      sessions.filter((session) => {
        if (filter === 'meeting')
          return session.scope === 'meeting' && session.meetingId === meetingId;
        return filter !== 'all-scope' || session.scope === 'all';
      }),
    [filter, meetingId, sessions],
  );
  const messageCount = active?.messages.length ?? 0;
  const scrollVersion = `${messageCount}-${streaming}`;
  useEffect(() => {
    void scrollVersion;
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
  }, [scrollVersion]);

  const handleScopeChange = (next: Scope) => {
    if (activeBase?.messages.length) return;
    setDraftScope(next);
    setActiveSessionId(null);
  };
  const newSession = async () => {
    const chatScope: ChatScope = scope;
    const session = await createChatSession({
      scope: chatScope,
      meeting_id: chatScope === 'meeting' ? meetingId : null,
    });
    setActiveSessionId(session.id);
    await queryClient.invalidateQueries({ queryKey: sessionsKey });
    return session;
  };
  const send = () => {
    const text = draft.trim();
    if (!text || (scope === 'meeting' && (!meetingId || !meetingFinal))) return;
    setDraft('');
    void streamMessage(text);
  };

  return {
    sessions: filteredSessions,
    active,
    filter,
    setFilter,
    scope,
    handleScopeChange,
    draft,
    setDraft,
    streamingId: streaming ? (activeSessionId ?? 'new') : null,
    msgsRef,
    newSession,
    send,
    cancel,
    setActiveSessionId,
    canSend: scope !== 'meeting' || (Boolean(meetingId) && meetingFinal),
    scopeLocked: Boolean(activeBase?.messages.length),
    isLoading: sessionsQuery.isLoading || (Boolean(activeSessionId) && sessionQuery.isLoading),
  };
};
