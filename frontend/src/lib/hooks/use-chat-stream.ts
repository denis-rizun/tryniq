'use client';

import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { streamChatMessage } from '@/lib/api/chat';
import { toChatMessage } from '@/lib/api/chat-adapters';
import type { ChatMessage, ChatSession } from '@/lib/types';

interface UseChatStreamOptions {
  activeBase: ChatSession | null | undefined;
  ensureSession: () => Promise<string | null>;
}

export const useChatStream = ({ activeBase, ensureSession }: UseChatStreamOptions) => {
  const queryClient = useQueryClient();
  const [streaming, setStreaming] = useState(false);
  const [pendingUser, setPendingUser] = useState<ChatMessage | null>(null);
  const [pendingAssistant, setPendingAssistant] = useState<ChatMessage | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const active = useMemo(() => {
    if (!activeBase) return null;
    const persistedIds = new Set(activeBase.messages.map((message) => message.id).filter(Boolean));
    const messages = [...activeBase.messages];
    if (pendingUser && !(pendingUser.id && persistedIds.has(pendingUser.id)))
      messages.push(pendingUser);
    if (pendingAssistant && !(pendingAssistant.id && persistedIds.has(pendingAssistant.id))) {
      messages.push(pendingAssistant);
    }
    return { ...activeBase, messages };
  }, [activeBase, pendingAssistant, pendingUser]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const send = useCallback(
    async (text: string) => {
      const sessionId = await ensureSession();
      if (!sessionId) return;

      setPendingUser({ role: 'user', text, pending: true });
      setPendingAssistant({ role: 'asst', text: '', pending: true });
      setStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;
      let accumulated = '';

      try {
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
                text: accumulated || 'Sorry, the assistant request failed.',
              });
            }
          },
        });
      } catch (error) {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setPendingAssistant({ role: 'asst', text: 'Sorry, the assistant request failed.' });
        }
      } finally {
        abortRef.current = null;
        setStreaming(false);
        await queryClient.invalidateQueries({ queryKey: ['chat', 'session', sessionId] });
        await queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] });
        setPendingUser(null);
        setPendingAssistant(null);
      }
    },
    [ensureSession, queryClient],
  );

  return { active, cancel, send, streaming };
};
