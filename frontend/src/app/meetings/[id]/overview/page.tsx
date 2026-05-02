'use client';

import { NotesPanel } from '@/components/meeting/notes/notes-panel';
import { TranscriptPanel } from '@/components/meeting/transcript/transcript-panel';
import { useLiveTranscript } from '@/lib/hooks/use-live-transcript';
import { meeting, people } from '@/lib/mock';

const OverviewPage = () => {
  const live = useLiveTranscript(meeting, true);
  return (
    <div className="overview">
      <TranscriptPanel
        meeting={meeting}
        people={people}
        isLive={true}
        activeSpeakerId={live.activeSpeakerId}
        currentUtterance={live.currentUtt}
        animatedUtterance={live.animatedUtt}
        flashId={live.flashId}
        outlinedId={live.outlinedId}
        onClickUtterance={live.onClickUtterance}
        onHoverUtterance={live.setHoveredUttId}
      />
      <NotesPanel
        meeting={meeting}
        people={people}
        onCiteClick={live.onCiteClick}
        flashNoteId={live.flashNoteId}
        hoveredUtteranceId={live.hoveredUttId}
        onHoverNote={live.setOutlinedId}
      />
    </div>
  );
};

export default OverviewPage;
