import type { Meeting } from '@/lib/types';

export const findUtteranceByTime = (meeting: Meeting, time: string) =>
  meeting.utterances.find((u) => u.time === time);
