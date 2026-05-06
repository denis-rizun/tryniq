import { Avatar } from '@/components/ui/avatar';
import type { Person } from '@/lib/types';

interface PersonRowProps {
  person: Person;
  meetingCount: number;
  lastSeenLabel: string;
  selected: boolean;
  onClick: () => void;
}

export const PersonRow = ({
  person,
  meetingCount,
  lastSeenLabel,
  selected,
  onClick,
}: PersonRowProps) => (
  <div
    onClick={onClick}
    className="person-row"
    style={{
      display: 'grid',
      gridTemplateColumns: '36px 1fr 100px 140px',
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
      {meetingCount} mtg{meetingCount === 1 ? '' : 's'}
    </div>
    <div className="mono" style={{ fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
      {lastSeenLabel}
    </div>
  </div>
);
