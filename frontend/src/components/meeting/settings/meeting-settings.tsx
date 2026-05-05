'use client';

import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import { useModels } from '@/lib/hooks/use-models';
import type { Meeting } from '@/lib/types';

export const MeetingSettings = ({ meeting }: { meeting: Meeting }) => {
  const { data: models } = useModels();
  const asrModel = models?.asr_final.model ?? '—';
  const llmModel = models?.metadata.model ?? '—';
  return (
    <div>
      <div className="settings-group">
        <SectionLabel>MODELS</SectionLabel>
        <div className="settings-row">
          <span style={{ fontSize: 13 }}>ASR (transcription)</span>
          <span className="mono" style={{ fontSize: 12, color: 'var(--color-ink-secondary)' }}>
            {asrModel}
          </span>
        </div>
        <div className="settings-row">
          <span style={{ fontSize: 13 }}>LLM (notes)</span>
          <span className="mono" style={{ fontSize: 12, color: 'var(--color-ink-secondary)' }}>
            {llmModel}
          </span>
        </div>
      </div>
      <div className="settings-group">
        <SectionLabel>AUDIO</SectionLabel>
        {meeting.participants.map((pid) => (
          <div key={pid} className="settings-row">
            <span style={{ fontSize: 13 }}>{pid}.wav</span>
            <button type="button" className="btn btn-sm">
              <Icon name="download" size={12} /> Download
            </button>
          </div>
        ))}
      </div>
      <div className="settings-group">
        <SectionLabel>VISIBILITY</SectionLabel>
        <div style={{ fontSize: 13, color: 'var(--color-ink-secondary)' }}>
          Meeting visible to participants. Org-wide visibility coming post-MVP.
        </div>
      </div>
      <div className="settings-group">
        <SectionLabel>DELETE MEETING</SectionLabel>
        <div style={{ fontSize: 13, color: 'var(--color-ink-secondary)', marginBottom: 12 }}>
          This permanently removes the recording, transcript, and derived notes.
        </div>
        <button type="button" className="btn btn-danger btn-sm">
          Delete meeting
        </button>
      </div>
    </div>
  );
};
