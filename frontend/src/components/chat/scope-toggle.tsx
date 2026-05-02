export type Scope = 'meeting' | 'all';

interface ScopeToggleProps {
  scope: Scope;
  onChange: (next: Scope) => void;
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

export const ScopeToggle = ({ scope, onChange }: ScopeToggleProps) => (
  <div className="scope-toggle">
    <button
      type="button"
      className={scope === 'meeting' ? 'active' : ''}
      onClick={() => onChange('meeting')}
      title="Searches only this meeting"
    >
      <Dot active={scope === 'meeting'} /> this meeting
    </button>
    <button
      type="button"
      className={scope === 'all' ? 'active' : ''}
      onClick={() => onChange('all')}
      title="Searches across every meeting you have access to."
    >
      <Dot active={scope === 'all'} /> all my meetings
    </button>
  </div>
);
