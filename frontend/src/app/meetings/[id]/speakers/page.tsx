'use client';

import { useQuery } from '@tanstack/react-query';
import { use } from 'react';
import { SpeakersPanel } from '@/components/meeting/speakers/speakers-panel';
import { getTranscript, listMeetings } from '@/lib/api/meetings';
import { toMeeting } from '@/lib/api/meetings-adapters';

interface Props {
  params: Promise<{ id: string }>;
}

const SpeakersPage = ({ params }: Props) => {
  const { id } = use(params);

  const transcriptQuery = useQuery({
    queryKey: ['transcript', id],
    queryFn: () => getTranscript(id),
  });
  const meetingsQuery = useQuery({
    queryKey: ['meetings'],
    queryFn: listMeetings,
  });

  if (transcriptQuery.isLoading) return <div className="empty">Loading…</div>;
  if (transcriptQuery.isError || !transcriptQuery.data) {
    return <div className="empty">Could not load meeting.</div>;
  }

  const title = meetingsQuery.data?.find((m) => m.id === id)?.title ?? 'Untitled meeting';
  const { meeting, people } = toMeeting(transcriptQuery.data, title);

  return <SpeakersPanel meeting={meeting} people={people} />;
};

export default SpeakersPage;
