'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { SectionLabel } from '@/components/ui/section-label';
import { Dropzone } from '@/components/upload/dropzone';
import { UploadProgress } from '@/components/upload/upload-progress';
import { STAGES } from '@/components/upload/upload-stages';
import { meeting } from '@/lib/mock';

const UploadPage = () => {
  const router = useRouter();
  const [stage, setStage] = useState(-1);

  useEffect(() => {
    if (stage < 0) return;
    if (stage >= STAGES.length) {
      router.push(`/meetings/${meeting.id}/overview`);
      return;
    }
    const t = setTimeout(() => setStage((s) => s + 1), stage === 2 ? 1500 : 900);
    return () => clearTimeout(t);
  }, [stage, router]);

  return (
    <div style={{ padding: '32px', maxWidth: 720, margin: '0 auto' }}>
      <SectionLabel>UPLOAD RECORDING</SectionLabel>
      {stage < 0 ? (
        <Dropzone onStart={() => setStage(0)} />
      ) : (
        <UploadProgress stage={stage} onCancel={() => setStage(-1)} />
      )}
    </div>
  );
};

export default UploadPage;
