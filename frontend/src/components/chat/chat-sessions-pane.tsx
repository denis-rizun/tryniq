import { SessionRow } from '@/components/chat/session-row';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import type { ChatSessionResponse } from '@/lib/api/chat';
import { toChatSessionList } from '@/lib/api/chat-adapters';

interface ChatSessionsPaneProps {
  activeSessionId: string | null;
  sessions: ChatSessionResponse[];
  onNew: () => void;
  onSelect: (sessionId: string) => void;
}

export const ChatSessionsPane = ({
  activeSessionId,
  sessions,
  onNew,
  onSelect,
}: ChatSessionsPaneProps) => (
  <aside className="chat-sessions-pane">
    <div className="chat-sessions-header">
      <SectionLabel>AI ASSISTANT</SectionLabel>
      <button type="button" className="btn btn-accent btn-sm mono" onClick={onNew}>
        <Icon name="plus" size={11} /> New
      </button>
    </div>
    {sessions.length === 0 && (
      <div className="chat-empty-sessions">No sessions yet. Type a message to start one.</div>
    )}
    {sessions.map((raw) => {
      const session = toChatSessionList(raw);
      return (
        <SessionRow
          key={session.id}
          session={session}
          isActive={session.id === activeSessionId}
          onClick={() => onSelect(session.id)}
          preview={raw.last_message_preview}
        />
      );
    })}
  </aside>
);
