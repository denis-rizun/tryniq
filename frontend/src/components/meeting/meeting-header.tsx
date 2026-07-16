'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Icon } from '@/components/ui/icon';
import type { MeetingStatus } from '@/lib/api/meetings';
import { listMeetings, renameMeeting } from '@/lib/api/meetings';
import { isActive } from '@/lib/api/meetings-adapters';
import { formatDuration } from '@/lib/format';
import { useUIStore } from '@/lib/store';

interface DurationBadgeProps {
  status: MeetingStatus | undefined;
  startedAt: string | undefined;
  endedAt: string | null | undefined;
}

const DurationBadge = ({ status, startedAt, endedAt }: DurationBadgeProps) => {
  const active = isActive(status);
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [active]);

  if (!startedAt) {
    return <span className="meeting-status meeting-status-idle mono">—</span>;
  }

  const startMs = new Date(startedAt).getTime();
  const endMs = endedAt ? new Date(endedAt).getTime() : null;
  const referenceMs = active ? Date.now() : (endMs ?? Date.now());
  const label = formatDuration((referenceMs - startMs) / 1000);

  const className = active
    ? 'meeting-status meeting-status-live'
    : 'meeting-status meeting-status-final';
  const dotClass = active ? 'meeting-status__dot rec-dot' : 'meeting-status__dot';

  return (
    <span className={className}>
      <span className={dotClass} />
      <span className="mono">{label}</span>
    </span>
  );
};

export const MeetingHeader = ({ meetingId }: { meetingId: string }) => {
  const { openExport, toggleDrawer } = useUIStore();
  const queryClient = useQueryClient();

  const meetingsQuery = useQuery({ queryKey: ['meetings'], queryFn: listMeetings });
  const meeting = meetingsQuery.data?.find((m) => m.id === meetingId);

  const titleRef = useRef<HTMLDivElement | null>(null);
  const renameMut = useMutation({
    mutationFn: (title: string) => renameMeeting(meetingId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
    },
  });

  useEffect(() => {
    if (!meeting || !titleRef.current) return;
    if (document.activeElement === titleRef.current) return;
    if (titleRef.current.textContent !== meeting.title) {
      titleRef.current.textContent = meeting.title;
    }
  }, [meeting]);

  const commitRename = () => {
    if (!meeting) return;
    const next = (titleRef.current?.textContent ?? '').trim();
    if (!next || next === meeting.title) {
      if (titleRef.current) titleRef.current.textContent = meeting.title;
      return;
    }
    renameMut.mutate(next);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      titleRef.current?.blur();
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      if (titleRef.current) titleRef.current.textContent = meeting?.title ?? '';
      titleRef.current?.blur();
    }
  };

  return (
    <div className="meeting-header">
      <div
        ref={titleRef}
        contentEditable
        suppressContentEditableWarning
        className="meeting-title"
        spellCheck={false}
        onBlur={commitRename}
        onKeyDown={onKeyDown}
      />
      <DurationBadge
        status={meeting?.status}
        startedAt={meeting?.started_at}
        endedAt={meeting?.ended_at}
      />
      <div style={{ flex: 1 }} />
      <button type="button" className="btn btn-sm" onClick={() => toggleDrawer()}>
        Ask AI <Icon name="arrow-up-right" size={11} />
      </button>
      <button type="button" className="btn btn-sm" onClick={() => openExport(meetingId)}>
        Export <Icon name="arrow-up-right" size={11} />
      </button>
    </div>
  );
};
