'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { SectionLabel } from '@/components/ui/section-label';
import { Dropzone } from '@/components/upload/dropzone';
import { UploadProgress } from '@/components/upload/upload-progress';
import { STAGES } from '@/components/upload/upload-stages';
import { subscribeMeetingEvents } from '@/lib/api/events';
import { uploadRecording } from '@/lib/api/meetings';
import type { MeetingLifecycleEvent } from '@/lib/api/types';

const EVENT_TO_STAGE: Partial<Record<MeetingLifecycleEvent['event'], number>> = {
  uploading: 0,
  normalizing: 1,
  diarizing: 1,
  transcribing: 2,
  finalizing: 3,
  final: STAGES.length,
};

const UploadPage = () => {
  const router = useRouter();
  const [stage, setStage] = useState(-1);
  const [error, setError] = useState<string | null>(null);
  const [meetingId, setMeetingId] = useState<string | null>(null);

  useEffect(() => {
    if (!meetingId) return;
    const unsubscribe = subscribeMeetingEvents(meetingId, {
      onEvent: (event) => {
        if (event.kind !== 'meeting_lifecycle') return;
        if (event.event === 'failed') {
          setError('Processing failed. Please try again.');
          return;
        }
        const next = EVENT_TO_STAGE[event.event];
        if (next === undefined) return;
        setStage((prev) => Math.max(prev, next));
        if (event.event === 'final') {
          router.push(`/meetings/${meetingId}/overview`);
        }
      },
    });
    return unsubscribe;
  }, [meetingId, router]);

  const handleFile = async (file: File) => {
    setError(null);
    setStage(0);
    try {
      const { meeting_id } = await uploadRecording(file);
      setMeetingId(meeting_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'upload failed');
      setStage(-1);
    }
  };

  const handleCancel = () => {
    setStage(-1);
    setMeetingId(null);
    setError(null);
  };

  return (
    <div style={{ padding: '32px', maxWidth: 720, margin: '0 auto' }}>
      <SectionLabel>UPLOAD RECORDING</SectionLabel>
      {stage < 0 ? (
        <Dropzone onFile={handleFile} />
      ) : (
        <UploadProgress stage={stage} onCancel={handleCancel} />
      )}
      {error && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            border: '1px solid var(--color-border)',
            borderRadius: 4,
            color: 'var(--color-accent-500)',
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
};

export default UploadPage;
