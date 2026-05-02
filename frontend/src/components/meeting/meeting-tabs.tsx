'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'graph', label: 'Graph' },
  { id: 'speakers', label: 'Speakers' },
  { id: 'settings', label: 'Settings' },
] as const;

export const MeetingTabs = ({ meetingId }: { meetingId: string }) => {
  const pathname = usePathname();
  return (
    <div className="tabs">
      {TABS.map((t) => {
        const href = `/meetings/${meetingId}/${t.id}`;
        const active = pathname === href;
        return (
          <Link key={t.id} href={href} className={cn('tab', active && 'active')}>
            {t.label}
          </Link>
        );
      })}
    </div>
  );
};
