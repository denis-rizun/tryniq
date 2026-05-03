'use client';

import { useQuery } from '@tanstack/react-query';
import { toMeetingListItem } from '@/lib/api/adapters';
import { listMeetings } from '@/lib/api/meetings';
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
