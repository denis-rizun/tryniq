'use client';

import { usePathname } from 'next/navigation';
import { Fragment } from 'react';
import { meeting } from '@/lib/mock';

const buildCrumbs = (pathname: string): string[] => {
  if (pathname === '/meetings') return ['Meetings'];
  if (pathname.startsWith('/meetings/') && pathname !== '/meetings/upload')
    return ['Meetings', meeting.title];
  if (pathname === '/upload') return ['Meetings', 'Upload'];
  if (pathname === '/people') return ['People'];
  if (pathname === '/chat') return ['AI assistant'];
  if (pathname === '/extension') return ['Extension popup'];
  return [];
};

export const Breadcrumb = () => {
  const pathname = usePathname();
  const crumbs = buildCrumbs(pathname);
  return (
    <span className="topbar-crumb">
      {crumbs.map((c, i) => (
        <Fragment key={c}>
          {i > 0 && <span className="sep">/</span>}
          <span>{c}</span>
        </Fragment>
      ))}
    </span>
  );
};
