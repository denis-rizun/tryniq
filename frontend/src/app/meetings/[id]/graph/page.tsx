'use client';

import { useQuery } from '@tanstack/react-query';
import { use } from 'react';
import { MeetingGraph } from '@/components/meeting/graph/meeting-graph';
import { getTranscript, listMeetings } from '@/lib/api/meetings';
import { toMeeting } from '@/lib/api/meetings-adapters';

interface Props {
  params: Promise<{ id: string }>;
}

const GraphPage = ({ params }: Props) => {
  const { id } = use(params);
  const transcriptQuery = useQuery({
    queryKey: ['transcript', id],
    queryFn: () => getTranscript(id),
  });
  const meetingsQuery = useQuery({ queryKey: ['meetings'], queryFn: listMeetings });

  if (transcriptQuery.isLoading) return <div className="empty">Loading…</div>;
  if (transcriptQuery.isError || !transcriptQuery.data) {
    return <div className="empty">Could not load meeting.</div>;
  }

  const title =
    meetingsQuery.data?.find((meeting) => meeting.id === id)?.title ?? 'Untitled meeting';
  return <MeetingGraph meeting={toMeeting(transcriptQuery.data, title).meeting} />;
};

export default GraphPage;
