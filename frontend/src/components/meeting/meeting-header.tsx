'use client';

import { AvatarStack } from '@/components/ui/avatar';
import { Icon } from '@/components/ui/icon';
import { RecIndicator } from '@/components/ui/status-dot';
import { meeting, people } from '@/lib/mock';
import { useUIStore } from '@/lib/store';

export const MeetingHeader = () => {
  const { setExportOpen, toggleDrawer } = useUIStore();
  return (
    <div className="meeting-header">
      <div
        contentEditable
        suppressContentEditableWarning
        className="meeting-title"
        spellCheck={false}
      >
        {meeting.title}
      </div>
      {meeting.durationLive && <RecIndicator time={meeting.durationLive} />}
      <AvatarStack people={meeting.participants.map((pid) => people[pid])} max={4} />
      <div style={{ flex: 1 }} />
      <button type="button" className="btn btn-sm" onClick={() => toggleDrawer()}>
        Ask AI <Icon name="arrow-up-right" size={11} />
      </button>
      <button type="button" className="btn btn-sm" onClick={() => setExportOpen(true)}>
        Export <Icon name="arrow-up-right" size={11} />
      </button>
    </div>
  );
};
