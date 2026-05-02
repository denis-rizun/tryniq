'use client';

import { useEffect, useState } from 'react';
import type { Meeting, Utterance } from '@/lib/types';

const START_INDEX = 11;
const TICK_MS = 5500;

export interface LiveTranscript {
  currentUtt: number;
  animatedUtt: number;
  flashId: string | null;
  outlinedId: string | null;
  flashNoteId: string | null;
  hoveredUttId: string | null;
  activeSpeakerId: string | undefined;
  setHoveredUttId: (id: string | null) => void;
  setOutlinedId: (id: string | null) => void;
  onClickUtterance: (u: Utterance) => void;
  onCiteClick: (time: string, noteId?: string) => void;
}

export const useLiveTranscript = (meeting: Meeting, enabled: boolean): LiveTranscript => {
  const [currentUtt, setCurrentUtt] = useState(START_INDEX);
  const [animatedUtt, setAnimatedUtt] = useState(START_INDEX);
  const [flashId, setFlashId] = useState<string | null>(null);
  const [outlinedId, setOutlinedId] = useState<string | null>(null);
  const [flashNoteId, setFlashNoteId] = useState<string | null>(null);
  const [hoveredUttId, setHoveredUttId] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    if (currentUtt >= meeting.utterances.length - 1) return;
    const t = setTimeout(() => {
      setCurrentUtt((i) => Math.min(i + 1, meeting.utterances.length - 1));
      setAnimatedUtt(currentUtt + 1);
    }, TICK_MS);
    return () => clearTimeout(t);
  }, [currentUtt, enabled, meeting.utterances.length]);

  const activeSpeakerId = meeting.utterances[currentUtt]?.speaker;

  const onClickUtterance = (u: Utterance) => {
    const items = [...meeting.decisions, ...meeting.actionItems, ...meeting.questions];
    const match = items.find((it) => it.time === u.time);
    if (match) {
      setFlashNoteId(match.id);
      setTimeout(() => setFlashNoteId(null), 900);
    }
  };

  const onCiteClick = (time: string) => {
    const u = meeting.utterances.find((uu) => uu.time === time);
    if (!u) return;
    setFlashId(u.id);
    setTimeout(() => setFlashId(null), 1000);
    const idx = meeting.utterances.indexOf(u);
    if (idx > currentUtt) {
      setCurrentUtt(idx);
      setAnimatedUtt(idx);
    }
  };

  return {
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
  };
};
