import { Icon } from '@/components/ui/icon';
import type { Scope } from './scope-toggle';

interface ComposerProps {
  draft: string;
  setDraft: (s: string) => void;
  onSend: () => void;
  scope: Scope;
  onToggleScope: () => void;
  disabled?: boolean;
  disabledReason?: string | null;
  streaming?: boolean;
  onCancel?: () => void;
}

export const AIDrawerComposer = ({
  draft,
  setDraft,
  onSend,
  scope,
  onToggleScope,
  disabled = false,
  disabledReason,
  streaming = false,
  onCancel,
}: ComposerProps) => {
  const placeholder = disabled
    ? (disabledReason ?? 'Unavailable')
    : scope === 'meeting'
      ? 'Ask anything about this meeting…'
      : 'Ask anything about your meetings…';

  return (
    <div className="chat-input-wrap">
      <textarea
        className="chat-textarea"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        disabled={disabled}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) {
            e.preventDefault();
            if (!disabled) onSend();
          }
        }}
        placeholder={placeholder}
      />
      <div
        style={{
          marginTop: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="scope-badge mono" style={{ cursor: 'pointer' }} onClick={onToggleScope}>
            {scope === 'meeting' ? 'this meeting' : 'all meetings'}
          </span>
          <span className="kbd mono">↵</span>
        </div>
        {streaming ? (
          <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>
            Stop
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={onSend}
            disabled={disabled || !draft.trim()}
            style={{ opacity: !disabled && draft.trim() ? 1 : 0.5 }}
          >
            <Icon name="send" size={12} color="var(--color-paper)" />
          </button>
        )}
      </div>
    </div>
  );
};
