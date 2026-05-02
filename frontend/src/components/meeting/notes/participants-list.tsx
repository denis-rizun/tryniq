import { Avatar } from '@/components/ui/avatar';
import type { Meeting, PeopleMap } from '@/lib/types';

interface ParticipantsListProps {
  meeting: Meeting;
  people: PeopleMap;
}

export const ParticipantsList = ({ meeting, people }: ParticipantsListProps) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
    {meeting.participants.map((pid) => {
      const p = people[pid];
      const pct = meeting.speakingTime[pid] || 0;
      return (
        <div key={pid} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Avatar person={p} />
          <span style={{ fontSize: 13, flex: 1 }}>{p.name}</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
            {pct}%
          </span>
        </div>
      );
    })}
  </div>
);
