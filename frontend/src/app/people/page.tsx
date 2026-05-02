'use client';

import { useState } from 'react';
import { PersonDrawer } from '@/components/people/person-drawer';
import { PersonRow } from '@/components/people/person-row';
import { SectionLabel } from '@/components/ui/section-label';
import { people } from '@/lib/mock';
import type { Person } from '@/lib/types';

const PeoplePage = () => {
  const [selected, setSelected] = useState<Person | null>(null);
  return (
    <>
      <div style={{ padding: '24px 32px', maxWidth: 900, position: 'relative' }}>
        <SectionLabel>PEOPLE</SectionLabel>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0, marginTop: 12 }}>
          {Object.values(people).map((p) => (
            <PersonRow
              key={p.id}
              person={p}
              selected={selected?.id === p.id}
              onClick={() => setSelected(p)}
            />
          ))}
        </div>
      </div>
      {selected && <PersonDrawer person={selected} onClose={() => setSelected(null)} />}
    </>
  );
};

export default PeoplePage;
