'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { Scope } from '@/components/chat/scope-toggle';
import {
  createChatSession,
  getChatSession,
  listChatSessions,
  streamChatMessage,
} from '@/lib/api/chat';
import {
  toChatMessage,
  toChatSessionDetail,
  toChatSessionList,
} from '@/lib/api/adapters';
import type { ChatScope } from '@/lib/api/types';
import { useUIStore } from '@/lib/store';
import type { ChatMessage, ChatSession } from '@/lib/types';

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
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [pendingAssistant, setPendingAssistant] = useState<ChatMessage | null>(null);
  const [pendingUser, setPendingUser] = useState<ChatMessage | null>(null);
  const msgsRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (open) {
      setFilter(defaultFilter);
      setDraftScope(defaultScope);
    }
  }, [open, defaultFilter, defaultScope]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const sessionsQuery = useQuery({
    queryKey: sessionsKey,
    queryFn: () => listChatSessions(),
    enabled: open,
  });

  const sessionQuery = useQuery({
    queryKey: activeSessionId ? sessionKey(activeSessionId) : ['chat', 'session', 'none'],
    queryFn: () => (activeSessionId ? getChatSession(activeSessionId) : Promise.resolve(null)),
    enabled: open && !!activeSessionId,
  });

  const sessions: ChatSession[] = useMemo(
    () => (sessionsQuery.data ?? []).map(toChatSessionList),
    [sessionsQuery.data],
  );

  const activeBase: ChatSession | undefined = useMemo(() => {
    if (sessionQuery.data) return toChatSessionDetail(sessionQuery.data);
    return sessions.find((s) => s.id === activeSessionId);
  }, [sessionQuery.data, sessions, activeSessionId]);

  const active: ChatSession | undefined = useMemo(() => {
    if (!activeBase) return undefined;
    const persistedIds = new Set(
      activeBase.messages.map((m) => m.id).filter((id): id is string => !!id),
    );
    const merged = [...activeBase.messages];
    if (pendingUser && !(pendingUser.id && persistedIds.has(pendingUser.id))) {
      merged.push(pendingUser);
    }
    if (pendingAssistant && !(pendingAssistant.id && persistedIds.has(pendingAssistant.id))) {
      merged.push(pendingAssistant);
    }
    return { ...activeBase, messages: merged };
  }, [activeBase, pendingAssistant, pendingUser]);

  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      if (filter === 'meeting') return s.scope === 'meeting' && s.meetingId === meetingId;
      if (filter === 'all-scope') return s.scope === 'all';
      return true;
    });
  }, [sessions, filter, meetingId]);

  const messageCount = active?.messages.length ?? 0;
  useEffect(() => {
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
  }, [messageCount, streamingId]);

  const persistedMessageCount = activeBase?.messages.length ?? 0;
  const scopeLocked = persistedMessageCount > 0;
  const scope: Scope = activeBase?.scope ?? draftScope;

  const handleScopeChange = (next: Scope) => {
    if (scopeLocked) return;
    setDraftScope(next);
    setActiveSessionId(null);
  };

  const createMutation = useMutation({
    mutationFn: createChatSession,
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: sessionsKey });
      setActiveSessionId(session.id);
    },
  });

  const newSession = async () => {
    const meetingScope: ChatScope = scope;
    return createMutation.mutateAsync({
      scope: meetingScope,
      meeting_id: meetingScope === 'meeting' ? meetingId : null,
    });
  };

  const ensureSession = async (): Promise<string> => {
    if (active && active.scope === scope) return active.id;
    const created = await newSession();
    return created.id;
  };

  const cancel = () => {
    abortRef.current?.abort();
    abortRef.current = null;
  };

  const send = async () => {
    const text = draft.trim();
    if (!text) return;
    if (scope === 'meeting' && (!meetingId || !meetingFinal)) return;

    let sessionId: string;
    try {
      sessionId = await ensureSession();
    } catch {
      return;
    }
    setActiveSessionId(sessionId);
    setDraft('');

    const tempUser: ChatMessage = { role: 'user', text, pending: true };
    const tempAssistant: ChatMessage = { role: 'asst', text: '', pending: true };
    setPendingUser(tempUser);
    setPendingAssistant(tempAssistant);
    setStreamingId(sessionId);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      let accumulated = '';
      await streamChatMessage(sessionId, text, {
        signal: controller.signal,
        onEvent: (event) => {
          if (event.kind === 'message_started') {
            setPendingUser({ ...toChatMessage(event.user_message), pending: false });
          } else if (event.kind === 'token') {
            accumulated += event.delta;
            setPendingAssistant({ role: 'asst', text: accumulated, pending: true });
          } else if (event.kind === 'message_completed') {
            setPendingAssistant(toChatMessage(event.message));
          } else if (event.kind === 'error') {
            setPendingAssistant({
              role: 'asst',
              text: accumulated || 'Sorry, I could not generate a response.',
            });
          }
        },
      });
    } catch (err) {
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        setPendingAssistant({
          role: 'asst',
          text: 'Sorry, the assistant request failed.',
        });
      }
    } finally {
      abortRef.current = null;
      setStreamingId(null);
      await queryClient.invalidateQueries({ queryKey: sessionKey(sessionId) });
      await queryClient.invalidateQueries({ queryKey: sessionsKey });
      setPendingUser(null);
      setPendingAssistant(null);
    }
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
    streamingId,
    msgsRef,
    newSession,
    send,
    cancel,
    setActiveSessionId,
    canSend: scope !== 'meeting' || (!!meetingId && meetingFinal),
    scopeLocked,
    isLoading: sessionsQuery.isLoading || (!!activeSessionId && sessionQuery.isLoading),
  };
};
