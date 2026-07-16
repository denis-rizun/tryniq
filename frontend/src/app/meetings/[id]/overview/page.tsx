'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { use, useEffect, useMemo } from 'react';
import { subscribeMeetingEvents } from '@/lib/api/events';
import { getTranscript, listMeetings } from '@/lib/api/meetings';
import { toMeeting } from '@/lib/api/meetings-adapters';
import { getMeetingMetadata } from '@/lib/api/metadata';
import { applyMeetingMetadata } from '@/lib/api/metadata-adapters';
import { OverviewClient } from './overview-client';

interface Props {
  params: Promise<{ id: string }>;
}

const OverviewPage = ({ params }: Props) => {
  const { id } = use(params);
  const queryClient = useQueryClient();

  const transcriptQuery = useQuery({
    queryKey: ['transcript', id],
    queryFn: () => getTranscript(id),
  });
  const meetingsQuery = useQuery({
    queryKey: ['meetings'],
    queryFn: listMeetings,
  });
  const metadataQuery = useQuery({
    queryKey: ['meeting-metadata', id],
    queryFn: () => getMeetingMetadata(id),
  });

  useEffect(() => {
    const unsubscribe = subscribeMeetingEvents(id, {
      onEvent: (event) => {
        if (event.kind === 'meeting_lifecycle' && event.event === 'metadata_ready') {
          queryClient.invalidateQueries({ queryKey: ['meeting-metadata', id] });
        }
      },
    });
    return () => unsubscribe();
  }, [id, queryClient]);

  const adapted = useMemo(() => {
    if (!transcriptQuery.data) return null;
    const title = meetingsQuery.data?.find((m) => m.id === id)?.title ?? 'Untitled meeting';
    const out = toMeeting(transcriptQuery.data, title);
    if (metadataQuery.data) {
      out.meeting = applyMeetingMetadata(out.meeting, metadataQuery.data);
    }
    return out;
  }, [id, meetingsQuery.data, metadataQuery.data, transcriptQuery.data]);

  if (transcriptQuery.isLoading) {
    return <div className="empty">Loading…</div>;
  }
  if (transcriptQuery.isError || !adapted) {
    return <div className="empty">Could not load meeting transcript.</div>;
  }

  return (
    <OverviewClient
      meeting={adapted.meeting}
      people={adapted.people}
      participantSlugById={adapted.participantSlugById}
    />
  );
};

export default OverviewPage;
