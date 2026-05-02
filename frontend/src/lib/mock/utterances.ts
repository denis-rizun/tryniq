import type { Utterance } from '@/lib/types';
import raw from './utterances.data.json';

type Tuple = [string, string, string, string, number, number[]];

export const utterances: Utterance[] = (raw as Tuple[]).map(
  ([id, speaker, time, text, confidence, lowWords]) => ({
    id,
    speaker,
    time,
    text,
    confidence,
    lowWords,
    final: true,
  }),
);
