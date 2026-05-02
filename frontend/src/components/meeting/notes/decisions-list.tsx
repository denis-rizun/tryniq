import { Cite } from '@/components/ui/cite';
import type { Meeting } from '@/lib/types';
import { cn } from '@/lib/utils';
import { findUtteranceByTime } from './notes-context';

interface DecisionsListProps {
  meeting: Meeting;
  flashNoteId: string | null;
  hoveredUtteranceId: string | null;
  onCiteClick: (time: string, noteId: string) => void;
  onHoverNote: (id: string | null) => void;
}

export const DecisionsList = ({
  meeting,
  flashNoteId,
  hoveredUtteranceId,
  onCiteClick,
  onHoverNote,
}: DecisionsListProps) => (
  <>
    {meeting.decisions.map((d) => {
      const sourced = findUtteranceByTime(meeting, d.time);
      const outlined = !!hoveredUtteranceId && sourced?.id === hoveredUtteranceId;
      const [first, ...rest] = d.text.split('.');
      const tail = rest.join('.').trim();
      return (
        <div
          key={d.id}
          className={cn(
            'note-item',
            !d.owner && 'action',
            flashNoteId === d.id && 'flash-in',
            outlined && 'flash-in',
          )}
          onClick={() => onCiteClick(d.time, d.id)}
          onMouseEnter={() => onHoverNote(sourced?.id ?? null)}
          onMouseLeave={() => onHoverNote(null)}
        >
          <span className="note-bullet">·</span>
          <span style={{ color: 'var(--color-decision)', fontWeight: 600 }}>{first}.</span>
          {tail && <span> {tail}</span>}
          <Cite time={d.time} onClick={(t) => onCiteClick(t, d.id)} />
          {!d.owner && <span className="note-meta-tertiary">no owner assigned</span>}
        </div>
      );
    })}
  </>
);
