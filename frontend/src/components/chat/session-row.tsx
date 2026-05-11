import { stripMarkdown } from '@/lib/format';
import type { ChatSession } from '@/lib/types';
import { cn } from '@/lib/utils';

interface SessionRowProps {
  session: ChatSession;
  isActive: boolean;
  onClick: (s: ChatSession) => void;
  preview?: string | null;
}

export const SessionRow = ({ session, isActive, onClick, preview }: SessionRowProps) => {
  const rawPreview =
    preview ?? session.messages.find((m) => m.role === 'user')?.text ?? '(empty)';
  const previewText = stripMarkdown(rawPreview);
  return (
    <div className={cn('session-row', isActive && 'active')} onClick={() => onClick(session)}>
      <div className="session-title">
        <span
          className="status-dot"
          style={{
            background: isActive ? 'var(--color-accent-500)' : 'var(--color-ink-tertiary)',
            width: 6,
            height: 6,
          }}
        />
        <span
          style={{
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {session.title}
        </span>
        <span className="scope-badge">
          {session.scope === 'meeting' ? 'this meeting' : 'all meetings'}
        </span>
      </div>
      <div className="session-preview">{previewText}</div>
      <div className="session-meta">{session.relTime}</div>
    </div>
  );
};
