import { Avatar } from '@/components/ui/avatar';
import type { Person } from '@/lib/types';

interface PersonRowProps {
  person: Person;
  selected: boolean;
  onClick: () => void;
}

const computeStats = (id: string) => {
  const code = id.charCodeAt(2);
  return {
    meetings: (code % 9) + 2,
    daysAgo: (code % 14) + 1,
    pct: 85 + (code % 10),
  };
};

export const PersonRow = ({ person, selected, onClick }: PersonRowProps) => {
  const stats = computeStats(person.id);
  return (
    <div
      onClick={onClick}
      className="person-row"
      style={{
        display: 'grid',
        gridTemplateColumns: '36px 1fr 80px 120px 200px',
        alignItems: 'center',
        gap: 16,
        padding: '12px 12px',
        borderBottom: '1px solid var(--color-border-subtle)',
        cursor: 'pointer',
        borderLeft: selected ? '2px solid var(--color-accent-500)' : '2px solid transparent',
        background: selected ? 'var(--color-paper-active)' : 'transparent',
      }}
    >
      <Avatar person={person} size="md" />
      <div style={{ fontSize: 13, fontWeight: 600 }}>{person.name}</div>
      <div className="mono" style={{ fontSize: 12, color: 'var(--color-ink-secondary)' }}>
        {stats.meetings} mtgs
      </div>
      <div className="mono" style={{ fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
        {person.id === 'p_anna' ? 'today' : `${stats.daysAgo}d ago`}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div className="speak-bar" style={{ flex: 1 }}>
          <div
            className="speak-bar-fill"
            style={{ width: `${stats.pct}%`, background: 'var(--color-decision)' }}
          />
        </div>
        <span className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
          {stats.pct}%
        </span>
      </div>
    </div>
  );
};
