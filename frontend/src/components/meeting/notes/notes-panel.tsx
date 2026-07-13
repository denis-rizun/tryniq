'use client';

import type { Meeting, PeopleMap } from '@/lib/types';
import { ActionsList } from './actions-list';
import { DecisionsList } from './decisions-list';
import { NotesSection } from './notes-section';
import { ParticipantsList } from './participants-list';
import { QuestionsList } from './questions-list';

interface NotesPanelProps {
  meeting: Meeting;
  people: PeopleMap;
  onCiteClick: (time: string, noteId: string) => void;
  flashNoteId: string | null;
  hoveredUtteranceId: string | null;
  onHoverNote: (id: string | null) => void;
}

export const NotesPanel = ({
  meeting,
  people,
  onCiteClick,
  flashNoteId,
  hoveredUtteranceId,
  onHoverNote,
}: NotesPanelProps) => {
  const noteProps = { meeting, flashNoteId, hoveredUtteranceId, onCiteClick, onHoverNote };
  const generating = !meeting.metadataGeneratedAt && meeting.state !== 'live';
  return (
    <div className="overview-right scroll-y">
      <NotesSection label="SUMMARY">
        <div
          style={{
            fontSize: 13,
            lineHeight: 1.55,
            whiteSpace: 'pre-wrap',
            color: meeting.summary ? 'var(--color-ink)' : 'var(--color-ink-tertiary)',
          }}
        >
          {meeting.summary || (generating ? 'Generating summary…' : 'No summary yet.')}
        </div>
      </NotesSection>

      <NotesSection label="DECISIONS" count={meeting.decisions.length}>
        <DecisionsList {...noteProps} />
      </NotesSection>

      <NotesSection label="ACTION ITEMS" count={meeting.actionItems.length}>
        <ActionsList {...noteProps} people={people} />
      </NotesSection>

      <NotesSection label="OPEN QUESTIONS" count={meeting.questions.length}>
        <QuestionsList {...noteProps} />
      </NotesSection>

      <NotesSection label="TOPICS" count={meeting.topics.length}>
        {meeting.topics.map((t) => (
          <div key={t.id} className="note-item" style={{ borderLeft: 'none', paddingLeft: 12 }}>
            <span className="note-bullet">·</span>
            <strong style={{ fontWeight: 600 }}>{t.name}</strong>
            <div style={{ fontSize: 12, color: 'var(--color-ink-secondary)', marginTop: 2 }}>
              {t.summary}
            </div>
          </div>
        ))}
      </NotesSection>

      <NotesSection label="PARTICIPANTS">
        <ParticipantsList meeting={meeting} people={people} />
      </NotesSection>

      <NotesSection
        label="RELATED PAST MEETINGS"
        count={meeting.previousMeetings.length || undefined}
      >
        {meeting.previousMeetings.length === 0 ? (
          <div
            className="note-item"
            style={{
              borderLeft: 'none',
              paddingLeft: 0,
              fontSize: 12,
              color: 'var(--color-ink-tertiary)',
            }}
          >
            No related meetings.
          </div>
        ) : (
          meeting.previousMeetings.map((prev) => (
            <div key={prev.id} className="note-item" style={{ borderLeft: 'none', paddingLeft: 0 }}>
              <span className="mono" style={{ fontSize: 11, color: 'var(--color-ink-tertiary)' }}>
                {prev.date}
              </span>
              <span style={{ marginLeft: 8 }}>
                <a
                  href={`/meetings/${prev.id}/overview`}
                  style={{
                    color: 'var(--color-accent-500)',
                    textDecoration: 'none',
                  }}
                >
                  {prev.title}
                </a>
              </span>
              {prev.relatedTopics.length > 0 ? (
                <div style={{ fontSize: 12, color: 'var(--color-ink-secondary)', marginTop: 2 }}>
                  Linked topics: {prev.relatedTopics.join(', ')}
                </div>
              ) : null}
            </div>
          ))
        )}
      </NotesSection>
    </div>
  );
};
