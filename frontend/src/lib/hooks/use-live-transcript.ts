'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { LiveEvent } from '@/lib/api/events';
import { subscribeMeetingEvents } from '@/lib/api/events';
import { formatTimestamp } from '@/lib/format';
import type { Meeting, Utterance } from '@/lib/types';

export type FinalizationPhase = 'live' | 'finalizing' | 'final';

const PARTIAL_FLAG = '__partial';

export interface LiveTranscript {
  utterances: Utterance[];
  currentUtt: number;
  animatedUtt: number;
  flashId: string | null;
  outlinedId: string | null;
  flashNoteId: string | null;
  hoveredUttId: string | null;
  activeSpeakerId: string | undefined;
  phase: FinalizationPhase;
  setHoveredUttId: (id: string | null) => void;
  setOutlinedId: (id: string | null) => void;
  onClickUtterance: (u: Utterance) => void;
  onCiteClick: (time: string, noteId?: string) => void;
}

export interface LiveTranscriptOptions {
  meetingId: string;
  enabled: boolean;
  participantSlugById: Record<string, string>;
  initialPhase?: FinalizationPhase;
}

export const useLiveTranscript = (
  meeting: Meeting,
  { meetingId, enabled, participantSlugById, initialPhase = 'live' }: LiveTranscriptOptions,
): LiveTranscript => {
  const [liveSegments, setLiveSegments] = useState<Utterance[]>([]);
  const [partials, setPartials] = useState<Record<string, Utterance>>({});
  const [flashId, setFlashId] = useState<string | null>(null);
  const [outlinedId, setOutlinedId] = useState<string | null>(null);
  const [flashNoteId, setFlashNoteId] = useState<string | null>(null);
  const [hoveredUttId, setHoveredUttId] = useState<string | null>(null);
  const [phase, setPhase] = useState<FinalizationPhase>(initialPhase);
  const seenUtteranceIds = useRef<Set<string>>(new Set(meeting.utterances.map((u) => u.id)));

  const slugByIdRef = useRef(participantSlugById);
  slugByIdRef.current = participantSlugById;

  useEffect(() => {
    if (!enabled) return;
    const resolveSpeaker = (participantId: string | null): string => {
      if (!participantId) return 'unknown';
      return slugByIdRef.current[participantId] ?? participantId;
    };
    const handleEvent = (event: LiveEvent) => {
      if (event.kind === 'transcript_segment') {
        if (seenUtteranceIds.current.has(event.utterance_id)) return;
        seenUtteranceIds.current.add(event.utterance_id);
        const u: Utterance = {
          id: event.utterance_id,
          speaker: resolveSpeaker(event.participant_id),
          time: formatTimestamp(event.t_start),
          text: event.text,
          confidence: 1,
          lowWords: [],
          final: event.is_final,
        };
        setLiveSegments((prev) => [...prev, u]);
        setPartials((prev) => {
          if (!event.stream_id || !prev[event.stream_id]) return prev;
          const next = { ...prev };
          delete next[event.stream_id];
          return next;
        });
      } else if (event.kind === 'partial_transcript') {
        setPartials((prev) => {
          const existing = prev[event.stream_id];
          if (existing && existing.text === event.text) return prev;
          const u: Utterance = {
            id: `${event.stream_id}-${PARTIAL_FLAG}`,
            speaker: resolveSpeaker(event.participant_id),
            time: '—',
            text: event.text,
            confidence: 0.5,
            lowWords: [],
            final: false,
          };
          return { ...prev, [event.stream_id]: u };
        });
      } else if (event.kind === 'meeting_lifecycle') {
        if (event.event === 'ended') {
          setPartials({});
        } else if (event.event === 'finalizing') {
          setPhase('finalizing');
          setPartials({});
        } else if (event.event === 'final') {
          setPhase('final');
          setPartials({});
          setLiveSegments([]);
          seenUtteranceIds.current = new Set();
        }
      }
    };

    const unsubscribe = subscribeMeetingEvents(meetingId, { onEvent: handleEvent });
    return () => unsubscribe();
  }, [enabled, meetingId]);

  const utterances = useMemo<Utterance[]>(() => {
    const partialList = Object.values(partials);
    return [...meeting.utterances, ...liveSegments, ...partialList];
  }, [meeting.utterances, liveSegments, partials]);

  const currentUtt = utterances.length === 0 ? 0 : utterances.length - 1;
  const animatedUtt = phase === 'live' ? currentUtt : -1;
  const activeSpeakerId = utterances[currentUtt]?.speaker;

  const onClickUtterance = (u: Utterance) => {
    const items = [...meeting.decisions, ...meeting.actionItems, ...meeting.questions];
    const match = items.find((it) => it.time === u.time);
    if (match) {
      setFlashNoteId(match.id);
      setTimeout(() => setFlashNoteId(null), 900);
    }
  };

  const onCiteClick = (time: string) => {
    const u = utterances.find((uu) => uu.time === time);
    if (!u) return;
    setFlashId(u.id);
    setTimeout(() => setFlashId(null), 1000);
  };

  return {
    utterances,
    currentUtt,
    animatedUtt,
    flashId,
    outlinedId,
    flashNoteId,
    hoveredUttId,
    activeSpeakerId,
    setHoveredUttId,
    setOutlinedId,
    onClickUtterance,
    onCiteClick,
    phase,
  };
};
