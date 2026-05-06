'use client';

import { useQuery } from '@tanstack/react-query';
import { Avatar } from '@/components/ui/avatar';
import { Backdrop } from '@/components/ui/backdrop';
import { Icon } from '@/components/ui/icon';
import { Pill } from '@/components/ui/pill';
import { SectionLabel } from '@/components/ui/section-label';
import { listPersonUtterances } from '@/lib/api/people';
import { formatTimestamp } from '@/lib/format';
import type { Person } from '@/lib/types';

interface PersonDrawerProps {
  person: Person;
  onClose: () => void;
}

const trim = (text: string, n: number): string =>
  text.length > n ? `${text.slice(0, n - 2)}…` : text;

export const PersonDrawer = ({ person, onClose }: PersonDrawerProps) => {
  const utterancesQuery = useQuery({
    queryKey: ['person-utterances', person.name],
    queryFn: () => listPersonUtterances(person.name, 6),
  });

  const utterances = utterancesQuery.data ?? [];

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
          <SectionLabel>RECENT UTTERANCES</SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 18 }}>
            {utterancesQuery.isLoading ? (
              <div style={{ fontSize: 12, color: 'var(--color-ink-tertiary)' }}>Loading…</div>
            ) : utterances.length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
                No utterances yet.
              </div>
            ) : (
              utterances.map((u) => (
                <div key={u.id} style={{ fontSize: 12, lineHeight: 1.5 }}>
                  <span
                    className="mono"
                    style={{ fontSize: 11, color: 'var(--color-ink-tertiary)', marginRight: 8 }}
                  >
                    {formatTimestamp(u.t_start)}
                  </span>
                  <span style={{ color: 'var(--color-ink-secondary)' }}>{trim(u.text, 110)}</span>
                  <div
                    className="mono"
                    style={{ fontSize: 10, color: 'var(--color-ink-tertiary)', marginTop: 2 }}
                  >
                    {u.meeting_title}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>
    </>
  );
};
