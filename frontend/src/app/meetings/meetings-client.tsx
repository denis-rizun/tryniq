'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { MeetingsTable } from '@/components/meetings-list/meetings-table';
import { MeetingsToolbar } from '@/components/meetings-list/meetings-toolbar';
import { SectionLabel } from '@/components/ui/section-label';
import { people } from '@/lib/mock';
import { useUIStore } from '@/lib/store';
import type { MeetingListItem } from '@/lib/types';

interface Props {
  meetings: MeetingListItem[];
  loadError: boolean;
}

export const MeetingsClient = ({ meetings, loadError }: Props) => {
  const router = useRouter();
  const [q, setQ] = useState('');
  const setExportOpen = useUIStore((s) => s.setExportOpen);

  const filtered = meetings.filter(
    (m) => !q || m.title.toLowerCase().includes(q.toLowerCase()),
  );

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1300, margin: '0 auto' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}
      >
        <SectionLabel>MEETINGS</SectionLabel>
      </div>
      <MeetingsToolbar query={q} setQuery={setQ} onUpload={() => router.push('/upload')} />
      {loadError ? (
        <div className="empty">Could not reach the API. Is the backend running?</div>
      ) : filtered.length === 0 ? (
        <div className="empty">No meetings yet. Start one or upload a recording.</div>
      ) : (
        <MeetingsTable
          meetings={filtered}
          people={people}
          onOpen={(id) => router.push(`/meetings/${id}/overview`)}
          onExport={() => setExportOpen(true)}
        />
      )}
    </div>
  );
};
