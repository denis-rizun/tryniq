'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import type { Meeting, PeopleMap, Utterance as UtteranceType } from '@/lib/types';
import { Utterance } from './utterance';

interface TranscriptPanelProps {
  meeting: Meeting;
  people: PeopleMap;
  isLive: boolean;
  activeSpeakerId: string | undefined;
  currentUtterance: number;
  animatedUtterance: number;
  flashId: string | null;
  outlinedId: string | null;
  onClickUtterance: (u: UtteranceType) => void;
  onHoverUtterance: (id: string | null) => void;
}

export const TranscriptPanel = ({
  meeting,
  people,
  isLive,
  activeSpeakerId,
  currentUtterance,
  animatedUtterance,
  flashId,
  outlinedId,
  onClickUtterance,
  onHoverUtterance,
}: TranscriptPanelProps) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [showLow, setShowLow] = useState(true);

  useEffect(() => {
    void currentUtterance;
    void animatedUtterance;
    if (!autoScroll) return;
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [currentUtterance, animatedUtterance, autoScroll]);

  useEffect(() => {
    if (!flashId) return;
    const target = scrollRef.current?.querySelector(`[data-utt-id="${flashId}"]`);
    if (target instanceof HTMLElement) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setAutoScroll(false);
    }
  }, [flashId]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 20;
    setAutoScroll(atBottom);
  };

  const visible = useMemo(
    () => meeting.utterances.slice(0, currentUtterance + 1),
    [meeting.utterances, currentUtterance],
  );

  return (
    <div
      className="overview-left scroll-y"
      ref={scrollRef}
      onScroll={handleScroll}
      onMouseLeave={() => onHoverUtterance(null)}
    >
      <SectionLabel
        right={
          <span className="mono" style={{ fontSize: 11, color: 'var(--color-ink-tertiary)' }}>
            {visible.length} utterances
          </span>
        }
      >
        TRANSCRIPT
      </SectionLabel>
      <div style={{ marginTop: 4 }}>
        {visible.map((u, i) => {
          const person = people[u.speaker] ?? {
            id: u.speaker,
            name: u.speaker,
            initials: u.speaker.slice(0, 2).toUpperCase(),
            color: 'var(--color-ink-tertiary)',
          };
          const isActive = isLive && u.speaker === activeSpeakerId && i === currentUtterance;
          const isLiveText = isLive && i === currentUtterance && !u.final;
          return (
            <div key={u.id} onMouseEnter={() => onHoverUtterance(u.id)}>
              <Utterance
                u={u}
                person={person}
                isActive={isActive}
                isLive={isLiveText}
                animate={i === animatedUtterance}
                flashId={flashId}
                outlinedId={outlinedId}
                showLowConf={showLow}
                onClick={onClickUtterance}
              />
            </div>
          );
        })}
      </div>
      {!autoScroll && isLive && (
        <button
          type="button"
          className="btn btn-accent btn-sm jump-live mono"
          onClick={() => setAutoScroll(true)}
          style={{ borderRadius: 999 }}
        >
          <Icon name="arrow-down" size={12} /> Jump to live
        </button>
      )}
      <div
        style={{
          marginTop: 24,
          paddingTop: 12,
          borderTop: '1px solid var(--color-border-subtle)',
        }}
      >
        <label
          className="mono"
          style={{
            fontSize: 11,
            color: 'var(--color-ink-secondary)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            cursor: 'pointer',
          }}
        >
          <Checkbox checked={showLow} onChange={setShowLow} />
          Show low-confidence words
        </label>
      </div>
    </div>
  );
};
