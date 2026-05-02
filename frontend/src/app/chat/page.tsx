'use client';

import { ChatMessage } from '@/components/chat/chat-message';
import { SessionRow } from '@/components/chat/session-row';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import { useUIStore } from '@/lib/store';

const ChatPage = () => {
  const { sessions, activeSessionId, setActiveSessionId } = useUIStore();
  const active = sessions.find((s) => s.id === activeSessionId) ?? sessions[0];

  return (
    <div
      style={{ display: 'grid', gridTemplateColumns: '320px 1fr', height: 'calc(100vh - 48px)' }}
    >
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
          <button type="button" className="btn btn-accent btn-sm mono">
            <Icon name="plus" size={11} /> New
          </button>
        </div>
        {sessions.map((s) => (
          <SessionRow
            key={s.id}
            session={s}
            isActive={s.id === active.id}
            onClick={(sess) => setActiveSessionId(sess.id)}
          />
        ))}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <SectionLabel>CURRENT SESSION</SectionLabel>
          <div className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
            {active.title} · {active.scope === 'meeting' ? 'this meeting' : 'all meetings'}
          </div>
        </div>
        <div
          className="scroll-y"
          style={{
            flex: 1,
            padding: '18px 24px',
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
            maxWidth: 720,
          }}
        >
          {active.messages.map((m, i) => (
            <ChatMessage key={i} m={m} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
