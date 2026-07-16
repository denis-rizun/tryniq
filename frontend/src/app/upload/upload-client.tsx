'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { SectionLabel } from '@/components/ui/section-label';
import { Dropzone } from '@/components/upload/dropzone';
import { UploadProgress } from '@/components/upload/upload-progress';
import { STAGES } from '@/components/upload/upload-stages';
import type { MeetingLifecycleEvent } from '@/lib/api/events';
import { subscribeMeetingEvents } from '@/lib/api/events';
import { uploadRecording } from '@/lib/api/meetings';

const eventToStage: Partial<Record<MeetingLifecycleEvent['event'], number>> = {
  uploading: 0,
  normalizing: 1,
  diarizing: 1,
  transcribing: 2,
  finalizing: 3,
  final: STAGES.length,
};
export const UploadClient = () => {
  const router = useRouter();
  const [stage, setStage] = useState(-1);
  const [error, setError] = useState<string | null>(null);
  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [fileName, setFileName] = useState('');
  useEffect(() => {
    if (!meetingId) return;
    return subscribeMeetingEvents(meetingId, {
      onEvent: (event) => {
        if (event.kind !== 'meeting_lifecycle') return;
        if (event.event === 'failed') {
          setError('Processing failed. Please try again.');
          return;
        }
        const next = eventToStage[event.event];
        if (next === undefined) return;
        setStage((current) => Math.max(current, next));
        if (event.event === 'final') router.push(`/meetings/${meetingId}/overview`);
      },
    });
  }, [meetingId, router]);
  const handleFile = async (file: File) => {
    setError(null);
    setFileName(file.name);
    setStage(0);
    try {
      const { meeting_id } = await uploadRecording(file);
      setMeetingId(meeting_id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'upload failed');
      setStage(-1);
    }
  };
  const cancel = () => {
    setStage(-1);
    setMeetingId(null);
    setFileName('');
    setError(null);
  };
  return (
    <div style={{ padding: '32px', maxWidth: 720, margin: '0 auto' }}>
      <SectionLabel>UPLOAD RECORDING</SectionLabel>
      {stage < 0 ? (
        <Dropzone onFile={handleFile} />
      ) : (
        <UploadProgress fileName={fileName} stage={stage} onCancel={cancel} />
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
