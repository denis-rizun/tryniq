'use client';

import { useQuery } from '@tanstack/react-query';
import { listMeetings } from '@/lib/api/meetings';
import { toMeetingListItem } from '@/lib/api/meetings-adapters';
import { MeetingsClient } from './meetings-client';

const MeetingsPage = () => {
  const { data, isError, isLoading } = useQuery({
    queryKey: ['meetings'],
    queryFn: listMeetings,
  });

  const meetings = (data ?? []).map(toMeetingListItem);
  const loadError = !isLoading && isError;

  return <MeetingsClient meetings={meetings} loadError={loadError} />;
};

export default MeetingsPage;
