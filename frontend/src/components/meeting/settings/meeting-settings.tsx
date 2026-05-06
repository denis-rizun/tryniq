'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import { downloadAudioTrack, listAudioTracks } from '@/lib/api/audio';
import { useModels } from '@/lib/hooks/use-models';
import type { Meeting } from '@/lib/types';

export const MeetingSettings = ({ meeting }: { meeting: Meeting }) => {
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const tracksQuery = useQuery({
    queryKey: ['meeting-audio', meeting.id],
    queryFn: () => listAudioTracks(meeting.id),
  });

  const onDownload = async (streamId: string, part: number) => {
    const key = `${streamId}:${part}`;
    setBusyKey(key);
    try {
      const { blob, filename } = await downloadAudioTrack(meeting.id, streamId, part);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename ?? `${streamId}.wav`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setBusyKey(null);
    }
  };
  const { data: models } = useModels();
  const asrLiveModel = models?.asr_live.model ?? '—';
  const asrFinalModel = models?.asr_final.model ?? '—';
  const llmModel = models?.metadata.model ?? '—';
  return (
    <div>
      <div className="settings-group">
        <SectionLabel>MODELS</SectionLabel>
        <div className="settings-row">
          <span style={{ fontSize: 13 }}>ASR (live)</span>
          <span className="mono" style={{ fontSize: 12, color: 'var(--color-ink-secondary)' }}>
            {asrLiveModel}
          </span>
        </div>
        <div className="settings-row">
          <span style={{ fontSize: 13 }}>ASR (post)</span>
          <span className="mono" style={{ fontSize: 12, color: 'var(--color-ink-secondary)' }}>
            {asrFinalModel}
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
        {tracksQuery.isLoading ? (
          <div style={{ fontSize: 12, color: 'var(--color-ink-tertiary)' }}>Loading tracks…</div>
        ) : tracksQuery.data && tracksQuery.data.length > 0 ? (
          tracksQuery.data.map((track) => {
            const key = `${track.stream_id}:${track.part}`;
            return (
              <div key={key} className="settings-row">
                <span style={{ fontSize: 13 }}>
                  {track.participant_name}
                  {track.part > 1 ? ` · part ${track.part}` : ''}
                  {track.is_local_user ? ' (You)' : ''}
                </span>
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={busyKey === key}
                  onClick={() => onDownload(track.stream_id, track.part)}
                >
                  <Icon name="download" size={12} />{' '}
                  {busyKey === key ? 'Downloading…' : 'Download'}
                </button>
              </div>
            );
          })
        ) : (
          <div style={{ fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
            No audio tracks available.
          </div>
        )}
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
