'use client';

import { use } from 'react';
import { MeetingGraph } from '@/components/meeting/graph/meeting-graph';
import { meeting as mockMeeting } from '@/lib/mock';

interface Props {
  params: Promise<{ id: string }>;
}

const GraphPage = ({ params }: Props) => {
  const { id } = use(params);
  return <MeetingGraph meeting={{ ...mockMeeting, id }} />;
};

export default GraphPage;
