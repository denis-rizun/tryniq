'use client';

import { Backdrop } from '@/components/ui/backdrop';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
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

export const AIAssistantDrawer = ({
  open,
  onClose,
  defaultFilter,
  defaultScope,
  onCiteJump,
}: AIAssistantDrawerProps) => {
  const d = useAIDrawer(open, defaultFilter, defaultScope);
  if (!open) return null;

  return (
    <>
      <Backdrop onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="AI Assistant">
        <div className="drawer-header">
          <span className="section-label" style={{ marginBottom: 0 }}>
            AI ASSISTANT
          </span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button type="button" className="btn btn-accent btn-sm mono" onClick={d.newSession}>
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
          active={d.active}
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
              <ScopeToggle scope={d.scope} onChange={d.handleScopeChange} />
              {d.scopeChanged && (
                <div style={{ marginTop: 6, fontSize: 11, color: 'var(--color-ink-secondary)' }}>
                  scope changed — future answers will use the new scope
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
            {d.active && d.active.messages.length === 0 && (
              <div style={{ fontSize: 13, color: 'var(--color-ink-tertiary)', padding: '20px 0' }}>
                Empty session. Ask anything about{' '}
                {d.scope === 'meeting' ? 'this meeting' : 'your meetings'}…
              </div>
            )}
            {d.active?.messages.map((m, i, arr) => (
              <ChatMessage
                key={i}
                m={m}
                onCite={onCiteJump}
                animate={!!m._animate && !!d.streamingMsg && i === arr.length - 1}
              />
            ))}
          </div>

          <AIDrawerComposer
            draft={d.draft}
            setDraft={d.setDraft}
            onSend={d.send}
            scope={d.scope}
            onToggleScope={() => d.handleScopeChange(d.scope === 'meeting' ? 'all' : 'meeting')}
          />
        </div>
      </aside>
    </>
  );
};
