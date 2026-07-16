import { type Scope, ScopeToggle } from '@/components/chat/scope-toggle';
import { Icon } from '@/components/ui/icon';
import type { MeetingResponse } from '@/lib/api/meetings';

interface ChatPageComposerProps {
  draft: string;
  finalMeetings: MeetingResponse[];
  meetingId: string | null;
  scope: Scope;
  scopeLocked: boolean;
  selectedMeeting: MeetingResponse | null;
  streaming: boolean;
  onChangeDraft: (draft: string) => void;
  onChangeMeeting: (meetingId: string | null) => void;
  onChangeScope: (scope: Scope) => void;
  onSend: () => void;
}

export const ChatPageComposer = ({
  draft,
  finalMeetings,
  meetingId,
  scope,
  scopeLocked,
  selectedMeeting,
  streaming,
  onChangeDraft,
  onChangeMeeting,
  onChangeScope,
  onSend,
}: ChatPageComposerProps) => {
  const sendDisabled = streaming || !draft.trim() || (scope === 'meeting' && !meetingId);
  return (
    <div className="chat-page-composer">
      <div className="chat-page-send-row">
        <textarea
          className="chat-textarea"
          value={draft}
          onChange={(event) => onChangeDraft(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === 'Enter' &&
              !event.shiftKey &&
              !event.metaKey &&
              !event.ctrlKey &&
              !event.altKey
            ) {
              event.preventDefault();
              onSend();
            }
          }}
          placeholder={
            scope === 'meeting'
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
          onClick={onSend}
          disabled={sendDisabled}
        >
          <Icon name="send" size={12} color="var(--color-paper)" /> Send
        </button>
      </div>
      <div className="chat-page-options">
        <div className="chat-page-scope-options">
          <ScopeToggle
            scope={scope}
            onChange={onChangeScope}
            disabled={scopeLocked}
            meetingDisabled={finalMeetings.length === 0}
            meetingDisabledTitle="No finalized meetings yet"
          />
          <span className="kbd mono" title="Enter to send, Shift+Enter for newline">
            ↵ send
          </span>
        </div>
        {scope === 'meeting' && (
          <div className="chat-page-meeting-picker">
            <span>about</span>
            {scopeLocked ? (
              <span className="mono">{selectedMeeting?.title ?? meetingId}</span>
            ) : (
              <select
                value={meetingId ?? ''}
                onChange={(event) => onChangeMeeting(event.target.value || null)}
                disabled={finalMeetings.length === 0}
              >
                {finalMeetings.length === 0 && <option value="">No meetings available</option>}
                {finalMeetings.map((meeting) => (
                  <option key={meeting.id} value={meeting.id}>
                    {meeting.title}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
