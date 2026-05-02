import { Cite } from '@/components/ui/cite';
import type { ActionItem, Meeting, PeopleMap } from '@/lib/types';
import { cn } from '@/lib/utils';
import { findUtteranceByTime } from './notes-context';

interface ActionsListProps {
  meeting: Meeting;
  people: PeopleMap;
  flashNoteId: string | null;
  hoveredUtteranceId: string | null;
  onCiteClick: (time: string, noteId: string) => void;
  onHoverNote: (id: string | null) => void;
}

const groupByOwner = (items: ActionItem[]): Record<string, ActionItem[]> => {
  const groups: Record<string, ActionItem[]> = { unassigned: [] };
  for (const a of items) {
    const k = a.owner || 'unassigned';
    if (!groups[k]) groups[k] = [];
    groups[k].push(a);
  }
  return groups;
};

export const ActionsList = ({
  meeting,
  people,
  flashNoteId,
  hoveredUtteranceId,
  onCiteClick,
  onHoverNote,
}: ActionsListProps) => {
  const grouped = groupByOwner(meeting.actionItems);
  const ownerName = (k: string) => (k === 'unassigned' ? 'Unassigned' : people[k]?.name || k);

  return (
    <>
      {Object.entries(grouped)
        .sort(([a], [b]) => (a === 'unassigned' ? -1 : b === 'unassigned' ? 1 : 0))
        .map(([owner, items]) => (
          <div key={owner} style={{ marginBottom: 12 }}>
            <div className="owner-group-label">
              For{' '}
              <strong style={{ color: 'var(--color-ink)', fontWeight: 600 }}>
                {ownerName(owner)}
              </strong>
            </div>
            {items.map((a) => {
              const sourced = findUtteranceByTime(meeting, a.time);
              const outlined = !!hoveredUtteranceId && sourced?.id === hoveredUtteranceId;
              return (
                <div
                  key={a.id}
                  className={cn(
                    'note-item',
                    owner === 'unassigned' && 'action',
                    flashNoteId === a.id && 'flash-in',
                    outlined && 'flash-in',
                  )}
                  onClick={() => onCiteClick(a.time, a.id)}
                  onMouseEnter={() => onHoverNote(sourced?.id ?? null)}
                  onMouseLeave={() => onHoverNote(null)}
                >
                  <span className="note-bullet">·</span>
                  {a.text}
                  <Cite time={a.time} onClick={(t) => onCiteClick(t, a.id)} />
                </div>
              );
            })}
          </div>
        ))}
    </>
  );
};
