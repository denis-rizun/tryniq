'use client';

import { useMemo } from 'react';
import { NotesPanel } from '@/components/meeting/notes/notes-panel';
import { TranscriptPanel } from '@/components/meeting/transcript/transcript-panel';
import { useLiveTranscript } from '@/lib/hooks/use-live-transcript';
import type { Meeting, PeopleMap } from '@/lib/types';

interface Props {
  meeting: Meeting;
  people: PeopleMap;
  participantSlugById: Record<string, string>;
}

export const OverviewClient = ({ meeting, people, participantSlugById }: Props) => {
  const live = useLiveTranscript(meeting, {
    meetingId: meeting.id,
    enabled: meeting.state === 'live' || meeting.state === 'finalizing',
    participantSlugById,
    initialPhase: meeting.state === 'final' ? 'final' : meeting.state,
  });

  const liveMeeting = useMemo<Meeting>(
    () => ({ ...meeting, utterances: live.utterances }),
    [meeting, live.utterances],
  );

  return (
    <div className="overview">
      <TranscriptPanel
        meeting={liveMeeting}
        people={people}
        isLive={meeting.state === 'live'}
        activeSpeakerId={live.activeSpeakerId}
        currentUtterance={live.currentUtt}
        animatedUtterance={live.animatedUtt}
        flashId={live.flashId}
        outlinedId={live.outlinedId}
        onClickUtterance={live.onClickUtterance}
        onHoverUtterance={live.setHoveredUttId}
      />
      <NotesPanel
        meeting={liveMeeting}
        people={people}
        onCiteClick={live.onCiteClick}
        flashNoteId={live.flashNoteId}
        hoveredUtteranceId={live.hoveredUttId}
        onHoverNote={live.setOutlinedId}
      />
    </div>
  );
};
