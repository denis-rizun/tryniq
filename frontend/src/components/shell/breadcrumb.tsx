'use client';

import { useQuery } from '@tanstack/react-query';
import { usePathname } from 'next/navigation';
import { Fragment } from 'react';
import { listMeetings } from '@/lib/api/meetings';

const MEETING_PATH_RE = /^\/meetings\/([^/]+)(?:\/.*)?$/;

const useMeetingTitle = (pathname: string): string | null => {
  const match = pathname.match(MEETING_PATH_RE);
  const meetingId = match?.[1];
  const isMeetingDetail = Boolean(meetingId) && meetingId !== 'upload';

  const meetingsQuery = useQuery({
    queryKey: ['meetings'],
    queryFn: listMeetings,
    enabled: isMeetingDetail,
  });

  if (!isMeetingDetail) return null;
  const meeting = meetingsQuery.data?.find((m) => m.id === meetingId);
  return meeting?.title ?? '…';
};

export const Breadcrumb = () => {
  const pathname = usePathname();
  const meetingTitle = useMeetingTitle(pathname);

  const buildCrumbs = (): string[] => {
    if (pathname === '/meetings') return ['Meetings'];
    if (pathname === '/meetings/upload') return ['Meetings', 'Upload'];
    if (meetingTitle !== null) return ['Meetings', meetingTitle];
    if (pathname === '/upload') return ['Meetings', 'Upload'];
    if (pathname === '/people') return ['People'];
    if (pathname === '/chat') return ['AI assistant'];
    if (pathname === '/extension') return ['Extension popup'];
    return [];
  };

  const crumbs = buildCrumbs();
  return (
    <span className="topbar-crumb">
      {crumbs.map((c, i) => (
        <Fragment key={`${i}-${c}`}>
          {i > 0 && <span className="sep">/</span>}
          <span>{c}</span>
        </Fragment>
      ))}
    </span>
  );
};
