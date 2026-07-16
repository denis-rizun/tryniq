'use client';

import { useQuery } from '@tanstack/react-query';
import { use, useMemo } from 'react';
import { MeetingSettings } from '@/components/meeting/settings/meeting-settings';
import { getTranscript, listMeetings } from '@/lib/api/meetings';
import { toMeeting } from '@/lib/api/meetings-adapters';

interface Props {
  params: Promise<{ id: string }>;
}

const SettingsPage = ({ params }: Props) => {
  const { id } = use(params);
  const transcriptQuery = useQuery({
    queryKey: ['transcript', id],
    queryFn: () => getTranscript(id),
  });
  const meetingsQuery = useQuery({
    queryKey: ['meetings'],
    queryFn: listMeetings,
  });

  const meeting = useMemo(() => {
    if (!transcriptQuery.data) return null;
    const title = meetingsQuery.data?.find((m) => m.id === id)?.title ?? 'Untitled meeting';
    return toMeeting(transcriptQuery.data, title).meeting;
  }, [id, meetingsQuery.data, transcriptQuery.data]);

  if (transcriptQuery.isLoading) {
    return <div className="empty">Loading…</div>;
  }
  if (transcriptQuery.isError || !meeting) {
    return <div className="empty">Could not load meeting.</div>;
  }

  return <MeetingSettings meeting={meeting} />;
};

export default SettingsPage;
