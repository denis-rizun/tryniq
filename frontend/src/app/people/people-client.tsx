'use client';

import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { PersonDrawer } from '@/components/people/person-drawer';
import { PersonRow } from '@/components/people/person-row';
import { SectionLabel } from '@/components/ui/section-label';
import { listPeople, type PersonListItemResponse } from '@/lib/api/people';
import { colorForId, formatRelativeShort, initialsOf } from '@/lib/format';
import type { Person } from '@/lib/types';

const toPerson = (item: PersonListItemResponse): Person => ({
  id: item.participant_ids[0] ?? item.name,
  name: item.is_local_user ? `${item.name} (You)` : item.name,
  initials: initialsOf(item.name),
  color: colorForId(item.participant_ids[0] ?? item.name),
});

export const PeopleClient = () => {
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const peopleQuery = useQuery({ queryKey: ['people'], queryFn: listPeople });
  const rows = useMemo(
    () => (peopleQuery.data ?? []).map((item) => ({ item, person: toPerson(item) })),
    [peopleQuery.data],
  );
  const selected = rows.find((row) => row.item.name === selectedName) ?? null;
  return (
    <div style={{ padding: '24px 32px', maxWidth: 900, position: 'relative' }}>
      <SectionLabel>PEOPLE</SectionLabel>
      {peopleQuery.isLoading ? (
        <div style={{ marginTop: 12, color: 'var(--color-ink-tertiary)', fontSize: 14 }}>
          Loading…
        </div>
      ) : rows.length === 0 ? (
        <div style={{ marginTop: 12, color: 'var(--color-ink-tertiary)', fontSize: 14 }}>
          No people yet.
        </div>
      ) : (
        <div style={{ marginTop: 12 }}>
          {rows.map(({ item, person }) => (
            <PersonRow
              key={item.name}
              person={person}
              meetingCount={item.meeting_count}
              lastSeenLabel={item.last_meeting_at ? formatRelativeShort(item.last_meeting_at) : '—'}
              selected={selectedName === item.name}
              onClick={() => setSelectedName(item.name)}
            />
          ))}
        </div>
      )}
      {selected && <PersonDrawer person={selected.person} onClose={() => setSelectedName(null)} />}
    </div>
  );
};
