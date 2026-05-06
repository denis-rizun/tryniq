'use client';

import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { PersonDrawer } from '@/components/people/person-drawer';
import { PersonRow } from '@/components/people/person-row';
import { SectionLabel } from '@/components/ui/section-label';
import { listPeople, type PersonListItemResponse } from '@/lib/api/people';
import type { Person } from '@/lib/types';

const AVATAR_COLORS = ['#A6B58F', '#C9A87A', '#B89AA5', '#9DA9B8', '#9C82A6', '#8FA6B5'];

const initialsOf = (name: string): string => {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

const colorFor = (id: string): string => {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
};

const formatLastSeen = (iso: string | null): string => {
  if (!iso) return '—';
  const ms = new Date(iso).getTime();
  if (Number.isNaN(ms)) return iso;
  const diffSec = Math.max(0, (Date.now() - ms) / 1000);
  if (diffSec < 60) return 'just now';
  const m = Math.floor(diffSec / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
};

const toPerson = (item: PersonListItemResponse): Person => {
  const id = item.participant_ids[0] ?? item.name;
  return {
    id,
    name: item.is_local_user ? `${item.name} (You)` : item.name,
    initials: initialsOf(item.name),
    color: colorFor(id),
  };
};

const PeoplePage = () => {
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const peopleQuery = useQuery({ queryKey: ['people'], queryFn: listPeople });

  const rows = useMemo(
    () =>
      (peopleQuery.data ?? []).map((item) => ({
        item,
        person: toPerson(item),
      })),
    [peopleQuery.data],
  );

  const selected = rows.find((r) => r.item.name === selectedName) ?? null;

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
              lastSeenLabel={formatLastSeen(item.last_meeting_at)}
              selected={selectedName === item.name}
              onClick={() => setSelectedName(item.name)}
            />
          ))}
        </div>
      )}
      {selected && (
        <PersonDrawer person={selected.person} onClose={() => setSelectedName(null)} />
      )}
    </div>
  );
};

export default PeoplePage;
