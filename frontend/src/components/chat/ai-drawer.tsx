'use client';

import { useQuery } from '@tanstack/react-query';
import { usePathname, useRouter } from 'next/navigation';
import { Backdrop } from '@/components/ui/backdrop';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import { getTranscript } from '@/lib/api/meetings';
import { useAIDrawer } from '@/lib/hooks/use-ai-drawer';
import { AIDrawerComposer } from './ai-drawer-composer';
import { AIDrawerSessions } from './ai-drawer-sessions';
import { ChatMessage } from './chat-message';
import { ScopeToggle } from './scope-toggle';

interface AIAssistantDrawerProps {
  open: boolean;
  onClose: () => void;
  defaultFilter: 'meeting' | 'all' | 'all-scope';
  defaultScope: 'meeting' | 'all';
  onCiteJump?: (time: string) => void;
}

const MEETING_PATH_RE = /^\/meetings\/([0-9a-f-]{36})/i;

export const AIAssistantDrawer = ({
  open,
  onClose,
  defaultFilter,
  defaultScope,
  onCiteJump,
}: AIAssistantDrawerProps) => {
  const pathname = usePathname();
  const router = useRouter();
  const meetingId = pathname?.match(MEETING_PATH_RE)?.[1] ?? null;

  const transcriptQuery = useQuery({
    queryKey: ['transcript', meetingId],
    queryFn: () => (meetingId ? getTranscript(meetingId) : Promise.resolve(null)),
    enabled: open && !!meetingId,
  });
  const meetingFinal = transcriptQuery.data?.status === 'final';

  const d = useAIDrawer(open, defaultFilter, defaultScope, { meetingId, meetingFinal });

  if (!open) return null;

  const handleCite = (c: { meetingId: string; tStart: number; label: string }) => {
    if (meetingId && c.meetingId === meetingId) {
      onCiteJump?.(c.label);
      return;
    }
    router.push(`/meetings/${c.meetingId}/overview?cite=${c.tStart}`);
    onClose();
  };

  const meetingScopeBlocked = d.scope === 'meeting' && (!meetingId || !meetingFinal);
  const blockedReason = !meetingId
    ? 'Open a meeting to chat about it.'
    : !meetingFinal
      ? 'Available after this meeting ends.'
      : null;

  return (
    <>
      <Backdrop onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="AI Assistant">
        <div className="drawer-header">
          <span className="section-label" style={{ marginBottom: 0 }}>
            AI ASSISTANT
          </span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              type="button"
              className="btn btn-accent btn-sm mono"
              onClick={() => {
                void d.newSession();
              }}
              disabled={d.scope === 'meeting' && !meetingId}
            >
              <Icon name="plus" size={11} /> New
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={onClose}
              aria-label="Close"
            >
              <Icon name="x" size={14} />
            </button>
          </div>
        </div>

        <AIDrawerSessions
          sessions={d.sessions}
          filter={d.filter}
          setFilter={d.setFilter}
          active={d.active ?? undefined}
          onSelect={d.setActiveSessionId}
        />

        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '14px 16px 0' }}>
            <SectionLabel>CURRENT SESSION</SectionLabel>
            <div style={{ marginBottom: 10 }}>
              <div
                className="mono"
                style={{
                  fontSize: 10,
                  color: 'var(--color-ink-secondary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.10em',
                  marginBottom: 6,
                }}
              >
                scope
              </div>
              <ScopeToggle
                scope={d.scope}
                onChange={d.handleScopeChange}
                disabled={d.scopeLocked}
                meetingDisabled={!meetingId || !meetingFinal}
                meetingDisabledTitle={
                  !meetingId
                    ? 'Open a meeting to use this scope'
                    : !meetingFinal
                      ? 'Available after this meeting ends'
                      : undefined
                }
              />
              {d.scopeLocked && (
                <div style={{ marginTop: 6, fontSize: 11, color: 'var(--color-ink-secondary)' }}>
                  scope is locked for this conversation
                </div>
              )}
            </div>
          </div>

          <div
            className="scroll-y"
            ref={d.msgsRef}
            style={{
              flex: 1,
              padding: '8px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: 14,
            }}
          >
            {d.active && d.active.messages.length === 0 && !d.streamingId && (
              <div style={{ fontSize: 13, color: 'var(--color-ink-tertiary)', padding: '20px 0' }}>
                Empty session. Ask anything about{' '}
                {d.scope === 'meeting' ? 'this meeting' : 'your meetings'}…
              </div>
            )}
            {!d.active && (
              <div style={{ fontSize: 13, color: 'var(--color-ink-tertiary)', padding: '20px 0' }}>
                {d.isLoading
                  ? 'Loading…'
                  : `No active session. Type a message to start ${
                      d.scope === 'meeting' ? 'a chat about this meeting' : 'a cross-meeting chat'
                    }.`}
              </div>
            )}
            {d.active?.messages.map((m, i, arr) => (
              <ChatMessage
                key={m.id ?? i}
                m={m}
                onCite={handleCite}
                animate={!!m.pending && i === arr.length - 1 && !!d.streamingId}
              />
            ))}
          </div>

          <AIDrawerComposer
            draft={d.draft}
            setDraft={d.setDraft}
            onSend={() => {
              void d.send();
            }}
            scope={d.scope}
            onToggleScope={() => d.handleScopeChange(d.scope === 'meeting' ? 'all' : 'meeting')}
            disabled={meetingScopeBlocked}
            disabledReason={meetingScopeBlocked ? blockedReason : null}
            streaming={!!d.streamingId}
            onCancel={d.cancel}
          />
        </div>
      </aside>
    </>
  );
};
