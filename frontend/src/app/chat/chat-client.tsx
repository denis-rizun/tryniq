'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChatMessage } from '@/components/chat/chat-message';
import { ChatPageComposer } from '@/components/chat/chat-page-composer';
import { ChatSessionsPane } from '@/components/chat/chat-sessions-pane';
import type { Scope } from '@/components/chat/scope-toggle';
import { SectionLabel } from '@/components/ui/section-label';
import { createChatSession, getChatSession, listChatSessions } from '@/lib/api/chat';
import { toChatSessionDetail } from '@/lib/api/chat-adapters';
import type { MeetingResponse } from '@/lib/api/meetings';
import { listMeetings } from '@/lib/api/meetings';
import { useChatStream } from '@/lib/hooks/use-chat-stream';
import { useUIStore } from '@/lib/store';
import type { ChatCitationView } from '@/lib/types';

export const ChatClient = () => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { activeSessionId, setActiveSessionId } = useUIStore();
  const [draft, setDraft] = useState('');
  const [draftScope, setDraftScope] = useState<Scope>('all');
  const [draftMeetingId, setDraftMeetingId] = useState<string | null>(null);
  const sessionsQuery = useQuery({
    queryKey: ['chat', 'sessions'],
    queryFn: () => listChatSessions(),
  });
  const sessionQuery = useQuery({
    queryKey: activeSessionId ? ['chat', 'session', activeSessionId] : ['chat', 'session', 'none'],
    queryFn: () => (activeSessionId ? getChatSession(activeSessionId) : Promise.resolve(null)),
    enabled: Boolean(activeSessionId),
  });
  const meetingsQuery = useQuery({
    queryKey: ['meetings'],
    queryFn: listMeetings,
    staleTime: 60_000,
  });
  const activeBase = useMemo(
    () => (sessionQuery.data ? toChatSessionDetail(sessionQuery.data) : null),
    [sessionQuery.data],
  );
  const finalMeetings = useMemo<MeetingResponse[]>(
    () => (meetingsQuery.data ?? []).filter((meeting) => meeting.status === 'final'),
    [meetingsQuery.data],
  );
  const ensureSession = useCallback(async () => {
    if (activeBase) return activeBase.id;
    if (draftScope === 'meeting' && !draftMeetingId) return null;
    const session = await createChatSession({
      scope: draftScope,
      meeting_id: draftScope === 'meeting' ? draftMeetingId : null,
    });
    setActiveSessionId(session.id);
    await queryClient.invalidateQueries({ queryKey: ['chat', 'sessions'] });
    return session.id;
  }, [activeBase, draftMeetingId, draftScope, queryClient, setActiveSessionId]);
  const { active, send, streaming } = useChatStream({ activeBase, ensureSession });
  const scopeLocked = Boolean(activeBase?.messages.length);
  const scope: Scope = active ? active.scope : draftScope;
  const meetingId = active ? active.meetingId : draftMeetingId;
  const selectedMeeting = useMemo(
    () => finalMeetings.find((meeting) => meeting.id === meetingId) ?? null,
    [finalMeetings, meetingId],
  );

  useEffect(() => {
    if (!active && draftScope === 'meeting' && !draftMeetingId && finalMeetings.length) {
      setDraftMeetingId(finalMeetings[0].id);
    }
  }, [active, draftMeetingId, draftScope, finalMeetings]);

  const startNew = () => {
    setActiveSessionId(null);
    setDraftScope('all');
    setDraftMeetingId(null);
  };
  const changeScope = (next: Scope) => {
    if (scopeLocked) return;
    if (active) setActiveSessionId(null);
    setDraftScope(next);
    if (next !== 'meeting') setDraftMeetingId(null);
  };
  const sendDraft = () => {
    const text = draft.trim();
    if (!text || streaming || (scope === 'meeting' && !meetingId)) return;
    setDraft('');
    void send(text);
  };
  const cite = (citation: ChatCitationView) =>
    router.push(`/meetings/${citation.meetingId}/overview?cite=${citation.tStart}`);

  return (
    <div className="chat-page">
      <ChatSessionsPane
        activeSessionId={activeSessionId}
        sessions={sessionsQuery.data ?? []}
        onNew={startNew}
        onSelect={setActiveSessionId}
      />
      <section className="chat-page-content">
        <header className="chat-page-header">
          <SectionLabel>CURRENT SESSION</SectionLabel>
          <div className="mono">
            {active
              ? `${active.title} · ${active.scope === 'meeting' ? 'this meeting' : 'all meetings'}`
              : scope === 'meeting'
                ? selectedMeeting
                  ? `New chat about: ${selectedMeeting.title}`
                  : 'New chat — pick a meeting below'
                : 'New cross-meeting chat'}
          </div>
        </header>
        <div className="chat-page-thread-wrap">
          <div className="chat-page-thread scroll-y">
            {active?.messages.length === 0 && !streaming && (
              <div>Type a message to start the conversation.</div>
            )}
            {!active && <div>Choose a scope below and ask anything.</div>}
            {active?.messages.map((message, index) => (
              <ChatMessage key={`${message.id ?? 'msg'}-${index}`} m={message} onCite={cite} />
            ))}
          </div>
          <ChatPageComposer
            draft={draft}
            finalMeetings={finalMeetings}
            meetingId={meetingId}
            scope={scope}
            scopeLocked={scopeLocked}
            selectedMeeting={selectedMeeting}
            streaming={streaming}
            onChangeDraft={setDraft}
            onChangeMeeting={setDraftMeetingId}
            onChangeScope={changeScope}
            onSend={sendDraft}
          />
        </div>
      </section>
    </div>
  );
};
