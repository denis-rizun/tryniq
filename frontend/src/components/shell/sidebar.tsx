'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Icon, type IconName } from '@/components/ui/icon';
import { StatusDot } from '@/components/ui/status-dot';
import { listMeetings } from '@/lib/api/meetings';
import { isActive as isActiveMeeting } from '@/lib/api/meetings-adapters';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  label: string;
  icon?: IconName;
  live?: boolean;
}

const PRIMARY: NavItem[] = [
  { href: '/meetings', label: 'Meetings', icon: 'meeting' },
  { href: '/upload', label: 'Upload', icon: 'upload' },
  { href: '/people', label: 'People', icon: 'people' },
  { href: '/chat', label: 'AI assistant', icon: 'message' },
];

const PROTOTYPE: NavItem[] = [{ href: '/extension', label: 'Extension popup', icon: 'sparkles' }];

const NavRow = ({ item, active }: { item: NavItem; active: boolean }) => (
  <Link href={item.href} className={cn('nav-item', active && 'active')}>
    {item.live ? (
      <span style={{ width: 14, display: 'inline-flex', justifyContent: 'center' }}>
        <StatusDot kind="live" />
      </span>
    ) : (
      item.icon && <Icon name={item.icon} size={14} />
    )}{' '}
    {item.label}
  </Link>
);

const isActive = (pathname: string, href: string): boolean => {
  if (href === '/meetings') return pathname === '/meetings';
  if (href.startsWith('/meetings/')) return pathname.startsWith('/meetings/');
  return pathname === href;
};

export const Sidebar = () => {
  const pathname = usePathname();
  const meetingsQuery = useQuery({ queryKey: ['meetings'], queryFn: listMeetings });
  const debriefMeeting = meetingsQuery.data?.find((meeting) => isActiveMeeting(meeting.status));
  const items = debriefMeeting
    ? [
        PRIMARY[0],
        { href: `/meetings/${debriefMeeting.id}/overview`, label: 'Debrief', live: true },
        ...PRIMARY.slice(1),
      ]
    : PRIMARY;
  return (
    <aside className="sidebar">
      <Link
        href="/meetings"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '4px 10px 18px',
          color: 'inherit',
          textDecoration: 'none',
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            background: 'var(--color-accent-500)',
            borderRadius: 2,
          }}
        />
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600 }}>
          tryniq
        </span>
      </Link>
      {items.map((item) => (
        <NavRow key={item.href} item={item} active={isActive(pathname, item.href)} />
      ))}
      <div className="nav-section">PROTOTYPE</div>
      {PROTOTYPE.map((item) => (
        <NavRow key={item.href} item={item} active={isActive(pathname, item.href)} />
      ))}
      <div style={{ position: 'absolute', bottom: 16, left: 8, right: 8 }}>
        <div
          style={{
            padding: '8px 10px',
            fontSize: 11,
            color: 'var(--color-ink-tertiary)',
            fontFamily: 'var(--font-mono)',
            borderTop: '1px solid var(--color-border-subtle)',
          }}
        >
          <div>v0.1 · open source</div>
          <div style={{ marginTop: 4 }}>May 11, 2026</div>
        </div>
      </div>
    </aside>
  );
};
