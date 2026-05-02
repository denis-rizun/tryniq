import { Avatar } from '@/components/ui/avatar';
import { Backdrop } from '@/components/ui/backdrop';
import { Icon } from '@/components/ui/icon';
import { Pill } from '@/components/ui/pill';
import { SectionLabel } from '@/components/ui/section-label';
import { meeting, people } from '@/lib/mock';
import type { Person } from '@/lib/types';

interface PersonDrawerProps {
  person: Person;
  onClose: () => void;
}

const trim = (text: string, n: number): string =>
  text.length > n ? `${text.slice(0, n - 2)}…` : text;

export const PersonDrawer = ({ person, onClose }: PersonDrawerProps) => {
  const recent = meeting.utterances.filter((u) => people[u.speaker]?.id === person.id).slice(0, 6);

  return (
    <>
      <Backdrop onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Person">
        <div className="drawer-header">
          <span className="section-label" style={{ marginBottom: 0 }}>
            PERSON
          </span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            <Icon name="x" size={14} />
          </button>
        </div>
        <div className="scroll-y" style={{ flex: 1, padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
            <Avatar person={person} size="lg" />
            <div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{person.name}</div>
              <div className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
                {person.id}
              </div>
            </div>
          </div>
          <SectionLabel>ALIASES</SectionLabel>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 18 }}>
            <Pill>{person.name.split(' ')[0].toLowerCase()}</Pill>
            <Pill>{person.initials.toLowerCase()}</Pill>
          </div>
          <SectionLabel>VOICE MATCH</SectionLabel>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
            <div className="speak-bar" style={{ flex: 1 }}>
              <div
                className="speak-bar-fill"
                style={{ width: '92%', background: 'var(--color-decision)' }}
              />
            </div>
            <span className="mono" style={{ fontSize: 11, color: 'var(--color-decision)' }}>
              92% confidence
            </span>
          </div>
          <SectionLabel>RECENT UTTERANCES</SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 18 }}>
            {recent.map((u) => (
              <div key={u.id} style={{ fontSize: 12, lineHeight: 1.5 }}>
                <span
                  className="mono"
                  style={{ fontSize: 11, color: 'var(--color-ink-tertiary)', marginRight: 8 }}
                >
                  {u.time}
                </span>
                <span style={{ color: 'var(--color-ink-secondary)' }}>{trim(u.text, 110)}</span>
              </div>
            ))}
            {recent.length === 0 && (
              <div style={{ fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
                No utterances in the current meeting.
              </div>
            )}
          </div>
          <SectionLabel>ACTIONS</SectionLabel>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button type="button" className="btn btn-sm">
              Merge with…
            </button>
            <button type="button" className="btn btn-sm">
              Split
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
