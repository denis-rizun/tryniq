'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChatMessage } from '@/components/chat/chat-message';
import { ScopeToggle, type Scope } from '@/components/chat/scope-toggle';
import { SessionRow } from '@/components/chat/session-row';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import {
  createChatSession,
  getChatSession,
  listChatSessions,
  streamChatMessage,
} from '@/lib/api/chat';
import { listMeetings } from '@/lib/api/meetings';
import { toChatMessage, toChatSessionDetail, toChatSessionList } from '@/lib/api/adapters';
import type { MeetingResponse } from '@/lib/api/types';
import { useUIStore } from '@/lib/store';
import type { ChatCitationView, ChatMessage as ChatMessageView } from '@/lib/types';

const ChatPage = () => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { activeSessionId, setActiveSessionId } = useUIStore();
  const [draft, setDraft] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [pendingUser, setPendingUser] = useState<ChatMessageView | null>(null);
  const [pendingAssistant, setPendingAssistant] = useState<ChatMessageView | null>(null);
  const [draftScope, setDraftScope] = useState<Scope>('all');
  const [draftMeetingId, setDraftMeetingId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const sessionsQuery = useQuery({
    queryKey: ['chat', 'sessions'],
    queryFn: () => listChatSessions(),
  });

  const sessionQuery = useQuery({
    queryKey: activeSessionId ? ['chat', 'session', activeSessionId] : ['chat', 'session', 'none'],
    queryFn: () => (activeSessionId ? getChatSession(activeSessionId) : Promise.resolve(null)),
    enabled: !!activeSessionId,
  });
  const activeBase = useMemo(
    () => (sessionQuery.data ? toChatSessionDetail(sessionQuery.data) : null),
    [sessionQuery.data],
  );

  const meetingsQuery = useQuery({
    queryKey: ['meetings'],
    queryFn: () => listMeetings(),
    staleTime: 60_000,
  });
  const finalMeetings = useMemo<MeetingResponse[]>(
    () => (meetingsQuery.data ?? []).filter((m) => m.status === 'final'),
    [meetingsQuery.data],
  );

  const active = useMemo(() => {
    if (!activeBase) return null;
    const merged = [...activeBase.messages];
    if (pendingUser) merged.push(pendingUser);
    if (pendingAssistant) merged.push(pendingAssistant);
    return { ...activeBase, messages: merged };
  }, [activeBase, pendingAssistant, pendingUser]);

  const persistedMessages = activeBase?.messages.length ?? 0;
  const scopeLocked = !!active && persistedMessages > 0;

  const effectiveScope: Scope = active ? active.scope : draftScope;
  const effectiveMeetingId: string | null = active ? active.meetingId : draftMeetingId;
  const selectedMeeting = useMemo(
    () => finalMeetings.find((m) => m.id === effectiveMeetingId) ?? null,
    [finalMeetings, effectiveMeetingId],
  );

  useEffect(() => {
    if (active) return;
    if (draftScope !== 'meeting') return;
    if (draftMeetingId) return;
    if (finalMeetings.length > 0) setDraftMeetingId(finalMeetings[0].id);
  }, [active, draftScope, draftMeetingId, finalMeetings]);

  const startNew = () => {
    setActiveSessionId(null);
    setDraftScope('all');
    setDraftMeetingId(null);
  };

  const handleScopeChange = (next: Scope) => {
    if (scopeLocked) return;
    if (active) setActiveSessionId(null);
    setDraftScope(next);
    if (next !== 'meeting') setDraftMeetingId(null);
  };

  const ensureSession = async (): Promise<string | null> => {
    if (active) return active.id;
    if (draftScope === 'meeting' && !draftMeetingId) return null;
    const created = await createChatSession({
      scope: draftScope,
      meeting_id: draftScope === 'meeting' ? draftMeetingId : null,
    });
    queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] });
    setActiveSessionId(created.id);
    return created.id;
  };

  const handleSend = async () => {
    const text = draft.trim();
    if (!text) return;
    if (effectiveScope === 'meeting' && !effectiveMeetingId) return;
    let sessionId: string | null;
    try {
      sessionId = await ensureSession();
    } catch {
      return;
    }
    if (!sessionId) return;
    setDraft('');
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
            setPendingUser({ ...toChatMessage(event.user_message) });
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
    } finally {
      abortRef.current = null;
      setStreaming(false);
      await queryClient.invalidateQueries({ queryKey: ['chat', 'session', sessionId] });
      await queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] });
      setPendingUser(null);
      setPendingAssistant(null);
    }
  };

  const handleCite = (c: ChatCitationView) => {
    router.push(`/meetings/${c.meetingId}/overview`);
  };

  const sendDisabled = streaming || !draft.trim() || (effectiveScope === 'meeting' && !effectiveMeetingId);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', height: 'calc(100vh - 48px)' }}>
      <div
        style={{
          borderRight: '1px solid var(--color-border)',
          padding: '18px 16px',
          overflow: 'auto',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 8,
          }}
        >
          <SectionLabel>AI ASSISTANT</SectionLabel>
          <button type="button" className="btn btn-accent btn-sm mono" onClick={startNew}>
            <Icon name="plus" size={11} /> New
          </button>
        </div>
        {(sessionsQuery.data ?? []).length === 0 && (
          <div style={{ fontSize: 12, color: 'var(--color-ink-tertiary)', padding: '8px 0' }}>
            No sessions yet. Type a message to start one.
          </div>
        )}
        {sessionsQuery.data?.map((raw) => {
          const s = toChatSessionList(raw);
          return (
            <SessionRow
              key={s.id}
              session={s}
              isActive={s.id === activeSessionId}
              onClick={() => setActiveSessionId(s.id)}
              preview={raw.last_message_preview}
            />
          );
        })}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid var(--color-border-subtle)',
            flexShrink: 0,
          }}
        >
          <SectionLabel>CURRENT SESSION</SectionLabel>
          <div className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
            {active
              ? `${active.title} · ${active.scope === 'meeting' ? 'this meeting' : 'all meetings'}`
              : draftScope === 'meeting'
                ? selectedMeeting
                  ? `New chat about: ${selectedMeeting.title}`
                  : 'New chat — pick a meeting below'
                : 'New cross-meeting chat'}
          </div>
        </div>

        <div
          style={{
            flex: 1,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            width: '100%',
            maxWidth: 820,
            margin: '0 auto',
            paddingBottom: 80,
          }}
        >
          <div
            className="scroll-y"
            style={{
              flex: 1,
              minHeight: 0,
              padding: '18px 24px',
              display: 'flex',
              flexDirection: 'column',
              gap: 14,
            }}
          >
            {active?.messages.length === 0 && !streaming && (
              <div style={{ fontSize: 13, color: 'var(--color-ink-tertiary)' }}>
                Type a message to start the conversation.
              </div>
            )}
            {!active && (
              <div style={{ fontSize: 13, color: 'var(--color-ink-tertiary)' }}>
                Choose a scope below and ask anything.
              </div>
            )}
            {active?.messages.map((m, i) => (
              <ChatMessage key={m.id ?? i} m={m} onCite={handleCite} />
            ))}
          </div>

          <div
            style={{
              padding: '14px 24px 0',
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <textarea
              className="chat-textarea"
              style={{ flex: 1, minHeight: 60, maxHeight: 180 }}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
              placeholder={
                effectiveScope === 'meeting'
                  ? selectedMeeting
                    ? `Ask anything about "${selectedMeeting.title}"…`
                    : 'Pick a meeting below to ask about it…'
                  : 'Ask anything across your meetings…'
              }
              disabled={streaming}
            />
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => void handleSend()}
              disabled={sendDisabled}
              style={{ alignSelf: 'flex-end' }}
            >
              <Icon name="send" size={12} color="var(--color-paper)" /> Send
            </button>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
              flexWrap: 'wrap',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <ScopeToggle
                scope={effectiveScope}
                onChange={handleScopeChange}
                disabled={scopeLocked}
                meetingDisabled={finalMeetings.length === 0}
                meetingDisabledTitle="No finalized meetings yet"
              />
              <span className="kbd mono" title="Enter to send, Shift+Enter for newline">
                ↵ send
              </span>
            </div>
            {effectiveScope === 'meeting' && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  fontSize: 12,
                  color: 'var(--color-ink-secondary)',
                }}
              >
                <span style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>about</span>
                {active ? (
                  <span className="mono" style={{ color: 'var(--color-ink)' }}>
                    {selectedMeeting?.title ?? effectiveMeetingId}
                  </span>
                ) : (
                  <select
                    value={draftMeetingId ?? ''}
                    onChange={(e) => setDraftMeetingId(e.target.value || null)}
                    disabled={scopeLocked || finalMeetings.length === 0}
                    style={{
                      padding: '4px 8px',
                      border: '1px solid var(--color-border)',
                      background: 'var(--color-paper)',
                      fontFamily: 'inherit',
                      fontSize: 12,
                      maxWidth: 280,
                    }}
                  >
                    {finalMeetings.length === 0 && <option value="">No meetings available</option>}
                    {finalMeetings.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.title}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </div>
        </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
