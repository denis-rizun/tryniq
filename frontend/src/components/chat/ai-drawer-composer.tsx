import { Icon } from '@/components/ui/icon';
import type { Scope } from './scope-toggle';

interface ComposerProps {
  draft: string;
  setDraft: (s: string) => void;
  onSend: () => void;
  scope: Scope;
  onToggleScope: () => void;
}

export const AIDrawerComposer = ({
  draft,
  setDraft,
  onSend,
  scope,
  onToggleScope,
}: ComposerProps) => (
  <div className="chat-input-wrap">
    <textarea
      className="chat-textarea"
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
          e.preventDefault();
          onSend();
        }
      }}
      placeholder={
        scope === 'meeting'
          ? 'Ask anything about this meeting…'
          : 'Ask anything about your meetings…'
      }
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
        <span className="kbd mono">⌘↵</span>
      </div>
      <button
        type="button"
        className="btn btn-primary btn-sm"
        onClick={onSend}
        disabled={!draft.trim()}
        style={{ opacity: draft.trim() ? 1 : 0.5 }}
      >
        <Icon name="send" size={12} color="var(--color-paper)" />
      </button>
    </div>
  </div>
);
