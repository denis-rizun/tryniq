import { Cite } from '@/components/ui/cite';
import type { Meeting } from '@/lib/types';
import { cn } from '@/lib/utils';
import { findUtteranceByTime } from './notes-context';

interface QuestionsListProps {
  meeting: Meeting;
  flashNoteId: string | null;
  hoveredUtteranceId: string | null;
  onCiteClick: (time: string, noteId: string) => void;
  onHoverNote: (id: string | null) => void;
}

export const QuestionsList = ({
  meeting,
  flashNoteId,
  hoveredUtteranceId,
  onCiteClick,
  onHoverNote,
}: QuestionsListProps) => (
  <>
    {meeting.questions.map((q) => {
      const sourced = findUtteranceByTime(meeting, q.time);
      const outlined = !!hoveredUtteranceId && sourced?.id === hoveredUtteranceId;
      return (
        <div
          key={q.id}
          className={cn('note-item', flashNoteId === q.id && 'flash-in', outlined && 'flash-in')}
          onClick={() => onCiteClick(q.time, q.id)}
          onMouseEnter={() => onHoverNote(sourced?.id ?? null)}
          onMouseLeave={() => onHoverNote(null)}
        >
          <span className="note-bullet">·</span>
          {q.stale && <span className="q-dot" />}
          {q.text}
          <Cite time={q.time} onClick={(t) => onCiteClick(t, q.id)} />
        </div>
      );
    })}
  </>
);
