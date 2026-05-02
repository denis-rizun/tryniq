import { redirect } from 'next/navigation';

interface Params {
  params: Promise<{ id: string }>;
}

const MeetingIndex = async ({ params }: Params) => {
  const { id } = await params;
  redirect(`/meetings/${id}/overview`);
};

export default MeetingIndex;
