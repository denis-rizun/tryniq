import type { ReactNode } from 'react';
import { MeetingHeader } from '@/components/meeting/meeting-header';
import { MeetingTabs } from '@/components/meeting/meeting-tabs';

interface LayoutProps {
  children: ReactNode;
  params: Promise<{ id: string }>;
}

const MeetingLayout = async ({ children, params }: LayoutProps) => {
  const { id } = await params;
  return (
    <>
      <MeetingHeader />
      <MeetingTabs meetingId={id} />
      {children}
    </>
  );
};

export default MeetingLayout;
