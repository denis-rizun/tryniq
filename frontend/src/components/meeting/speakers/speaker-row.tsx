import { Avatar } from '@/components/ui/avatar';
import { Icon } from '@/components/ui/icon';
import type { Person } from '@/lib/types';

export interface SpeakerEntry {
  p: Person;
  pct: number;
  utterCount: number;
  recognized: boolean;
}

interface SpeakerRowProps {
  speaker: SpeakerEntry;
  expanded: boolean;
  onToggle: () => void;
}

export const SpeakerRow = ({ speaker, expanded, onToggle }: SpeakerRowProps) => (
  <div className="speaker-row" onClick={onToggle}>
    <Avatar person={speaker.p} />
    <div style={{ fontSize: 13, fontWeight: 600 }}>{speaker.p.name}</div>
    <div className="speak-bar">
      <div className="speak-bar-fill" style={{ width: `${speaker.pct}%` }} />
    </div>
    <div className="mono" style={{ fontSize: 12, color: 'var(--color-ink-secondary)' }}>
      {speaker.pct}%
    </div>
    <div
      className="mono"
      style={{
        fontSize: 11,
        color: speaker.recognized ? 'var(--color-decision)' : 'var(--color-ink-tertiary)',
      }}
    >
      {speaker.recognized ? (
        <>
          <Icon name="check" size={12} /> recognized from past meetings
        </>
      ) : (
        'new voice'
      )}
    </div>
    <Icon
      name={expanded ? 'chevron-down' : 'chevron-right'}
      size={14}
      color="var(--color-ink-tertiary)"
    />
  </div>
);
