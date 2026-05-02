'use client';

import { useState } from 'react';
import { SectionLabel } from '@/components/ui/section-label';
import type { Meeting, PeopleMap } from '@/lib/types';
import { type SpeakerEntry, SpeakerRow } from './speaker-row';
import { SpeakerWaveform } from './speaker-waveform';

interface SpeakersPanelProps {
  meeting: Meeting;
  people: PeopleMap;
}

const buildSpeakers = (meeting: Meeting, people: PeopleMap): SpeakerEntry[] =>
  meeting.participants.map((pid) => ({
    p: people[pid],
    pct: meeting.speakingTime[pid] || 0,
    utterCount: meeting.utterances.filter((u) => u.speaker === pid).length,
    recognized: pid !== 'anna',
  }));

export const SpeakersPanel = ({ meeting, people }: SpeakersPanelProps) => {
  const [expanded, setExpanded] = useState<string | null>(null);
  const speakers = buildSpeakers(meeting, people);

  return (
    <div style={{ padding: '18px 0' }}>
      <div style={{ padding: '0 24px' }}>
        <SectionLabel>SPEAKERS</SectionLabel>
      </div>
      {speakers.map((s, i) => {
        const isOpen = expanded === s.p.id;
        return (
          <div key={s.p.id}>
            <SpeakerRow
              speaker={s}
              expanded={isOpen}
              onToggle={() => setExpanded(isOpen ? null : s.p.id)}
            />
            {isOpen && <SpeakerWaveform pct={s.pct} index={i} />}
          </div>
        );
      })}
    </div>
  );
};
