export type Scope = 'meeting' | 'all';

interface ScopeToggleProps {
  scope: Scope;
  onChange: (next: Scope) => void;
  disabled?: boolean;
  meetingDisabled?: boolean;
  meetingDisabledTitle?: string;
}

const Dot = ({ active }: { active: boolean }) => (
  <span
    style={{
      width: 6,
      height: 6,
      borderRadius: '50%',
      background: active ? 'var(--color-accent-500)' : 'transparent',
      border: active ? 'none' : '1px solid var(--color-ink-tertiary)',
    }}
  />
);

export const ScopeToggle = ({
  scope,
  onChange,
  disabled = false,
  meetingDisabled = false,
  meetingDisabledTitle,
}: ScopeToggleProps) => {
  const meetingBlocked = disabled || meetingDisabled;
  const allBlocked = disabled;
  return (
    <div className="scope-toggle" aria-disabled={disabled || undefined}>
      <button
        type="button"
        className={scope === 'meeting' ? 'active' : ''}
        onClick={() => !meetingBlocked && onChange('meeting')}
        disabled={meetingBlocked}
        title={
          meetingDisabled
            ? (meetingDisabledTitle ?? 'No meeting context available')
            : disabled
              ? 'Scope is locked once the conversation has started'
              : 'Searches only this meeting'
        }
        style={meetingBlocked ? { opacity: 0.5, cursor: 'not-allowed' } : undefined}
      >
        <Dot active={scope === 'meeting'} /> this meeting
      </button>
      <button
        type="button"
        className={scope === 'all' ? 'active' : ''}
        onClick={() => !allBlocked && onChange('all')}
        disabled={allBlocked}
        title={
          disabled
            ? 'Scope is locked once the conversation has started'
            : 'Searches across every meeting you have access to.'
        }
        style={allBlocked ? { opacity: 0.5, cursor: 'not-allowed' } : undefined}
      >
        <Dot active={scope === 'all'} /> all my meetings
      </button>
    </div>
  );
};
