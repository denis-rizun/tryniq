import { AvatarStack } from '@/components/ui/avatar';
import { Pill } from '@/components/ui/pill';
import { StatusDot } from '@/components/ui/status-dot';
import type { MeetingListItem, PeopleMap } from '@/lib/types';

interface MeetingsTableProps {
  meetings: MeetingListItem[];
  people: PeopleMap;
  onOpen: (id: string) => void;
  onExport: (id: string) => void;
}

export const MeetingsTable = ({ meetings, people, onOpen, onExport }: MeetingsTableProps) => (
  <table className="meetings-table">
    <thead>
      <tr>
        <th style={{ width: 24 }} />
        <th>Title</th>
        <th style={{ width: 120 }}>Started</th>
        <th style={{ width: 80 }}>Duration</th>
        <th style={{ width: 130 }}>Participants</th>
        <th>Topics</th>
        <th style={{ width: 90 }}>Decisions</th>
        <th style={{ width: 90 }}>Questions</th>
        <th style={{ width: 130 }} />
      </tr>
    </thead>
    <tbody>
      {meetings.map((m) => (
        <tr key={m.id} onClick={() => onOpen(m.id)}>
          <td>
            <StatusDot kind={m.state === 'live' ? 'live' : 'final'} />
          </td>
          <td style={{ fontWeight: 600 }}>{m.title}</td>
          <td
            className="mono"
            style={{ fontSize: 12, color: 'var(--color-ink-secondary)' }}
            title={m.startedAt}
          >
            {m.relativeStart}
          </td>
          <td className="mono" style={{ fontSize: 12, color: 'var(--color-ink-secondary)' }}>
            {m.duration || m.durationLive || '—'}
          </td>
          <td>
            {m.participants.length > 0 ? (
              <AvatarStack people={m.participants.map((pid) => people[pid])} max={4} />
            ) : (
              <span className="mono" style={{ fontSize: 12 }}>
                {m.participantsCount}
              </span>
            )}
          </td>
          <td>
            {m.topPills.length > 0 ? (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {m.topPills.map((t) => (
                  <Pill key={t}>{t}</Pill>
                ))}
              </div>
            ) : (
              <span className="mono" style={{ fontSize: 12 }}>
                {m.topicsCount}
              </span>
            )}
          </td>
          <td className="mono" style={{ fontSize: 12 }}>
            {m.decCount}
          </td>
          <td className="mono" style={{ fontSize: 12 }}>
            {m.qCount}
          </td>
          <td>
            <div className="row-actions">
              <button
                type="button"
                className="btn btn-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onExport(m.id);
                }}
              >
                Export
              </button>
            </div>
          </td>
        </tr>
      ))}
    </tbody>
  </table>
);
