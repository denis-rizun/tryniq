'use client';

import { useQuery } from '@tanstack/react-query';
import { use } from 'react';
import { toMeeting } from '@/lib/api/adapters';
import { getTranscript, listMeetings } from '@/lib/api/meetings';
import { OverviewClient } from './overview-client';

interface Props {
  params: Promise<{ id: string }>;
}

const OverviewPage = ({ params }: Props) => {
  const { id } = use(params);

  const transcriptQuery = useQuery({
    queryKey: ['transcript', id],
    queryFn: () => getTranscript(id),
  });
  const meetingsQuery = useQuery({
    queryKey: ['meetings'],
    queryFn: listMeetings,
  });

  if (transcriptQuery.isLoading) {
    return <div className="empty">Loading…</div>;
  }
  if (transcriptQuery.isError || !transcriptQuery.data) {
    return <div className="empty">Could not load meeting transcript.</div>;
  }

  const title =
    meetingsQuery.data?.find((m) => m.id === id)?.title ?? 'Untitled meeting';
  const { meeting, people, participantSlugById } = toMeeting(transcriptQuery.data, title);

  return (
    <OverviewClient meeting={meeting} people={people} participantSlugById={participantSlugById} />
  );
};

export default OverviewPage;
