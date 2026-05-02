import { SectionLabel } from '@/components/ui/section-label';
import type { ChatSession } from '@/lib/types';
import { cn } from '@/lib/utils';
import { SessionRow } from './session-row';

type Filter = 'meeting' | 'all' | 'all-scope';

interface SessionsProps {
  sessions: ChatSession[];
  filter: Filter;
  setFilter: (f: Filter) => void;
  active?: ChatSession;
  onSelect: (id: string) => void;
}

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all', label: 'all' },
  { id: 'meeting', label: 'this meeting' },
  { id: 'all-scope', label: 'cross-meeting' },
];

export const AIDrawerSessions = ({
  sessions,
  filter,
  setFilter,
  active,
  onSelect,
}: SessionsProps) => (
  <div
    style={{
      borderBottom: '1px solid var(--color-border-subtle)',
      maxHeight: '32%',
      display: 'flex',
      flexDirection: 'column',
    }}
  >
    <div style={{ padding: '14px 16px 8px' }}>
      <SectionLabel>SESSIONS</SectionLabel>
      <div style={{ display: 'flex', gap: 6 }}>
        {FILTERS.map((f) => (
          <span
            key={f.id}
            className={cn('filter-chip', filter === f.id && 'active')}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </span>
        ))}
      </div>
    </div>
    <div className="scroll-y" style={{ flex: 1, minHeight: 0 }}>
      {sessions.map((s) => (
        <SessionRow
          key={s.id}
          session={s}
          isActive={!!active && s.id === active.id}
          onClick={(sess) => onSelect(sess.id)}
        />
      ))}
      {sessions.length === 0 && (
        <div style={{ padding: '12px 16px', fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
          No sessions match this filter.
        </div>
      )}
    </div>
  </div>
);
