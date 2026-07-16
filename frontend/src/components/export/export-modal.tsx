'use client';

import { Backdrop } from '@/components/ui/backdrop';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import { ExportFormatRow } from './export-format-row';
import { ExportIncludeList } from './export-include-list';
import { useMeetingExport } from './use-meeting-export';

export const ExportModal = ({ meetingId, onClose }: { meetingId: string; onClose: () => void }) => {
  const state = useMeetingExport(meetingId);
  return (
    <>
      <Backdrop onClick={onClose} />
      <div className="modal" style={{ width: 520 }} role="dialog" aria-label="Export meeting">
        <div className="modal-header">
          <SectionLabel>EXPORT MEETING</SectionLabel>
          <div className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
            {state.meeting
              ? `${state.meeting.title} · ${state.meeting.started_at}`
              : 'Loading meeting…'}
          </div>
        </div>
        <div className="modal-body">
          <ExportIncludeList
            blocks={state.blocks}
            allOn={state.allOn}
            onToggle={state.toggle}
            onToggleAll={state.toggleAll}
          />
          <ExportFormatRow format={state.format} onChange={state.setFormat} />
          <SectionLabel>PREVIEW</SectionLabel>
          <pre
            className="mono scroll-y"
            style={{
              fontSize: 11,
              lineHeight: 1.5,
              background: 'var(--color-paper-hover)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: 4,
              padding: 12,
              margin: 0,
              maxHeight: 220,
              whiteSpace: 'pre-wrap',
              color: 'var(--color-ink)',
            }}
          >
            {state.preview}
          </pre>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          {state.error && (
            <span
              className="mono"
              style={{ fontSize: 11, color: 'var(--color-danger-500)', flex: 1, marginLeft: 8 }}
            >
              {state.error}
            </span>
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              className="btn"
              onClick={state.copy}
              disabled={state.busy !== null || state.format !== 'md'}
            >
              <Icon name="copy" size={12} />{' '}
              {state.copied ? 'Copied' : state.busy === 'copy' ? 'Copying…' : 'Copy to clipboard'}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={state.download}
              disabled={state.busy !== null || state.format !== 'md'}
            >
              <Icon name="download" size={12} color="var(--color-paper)" />{' '}
              {state.busy === 'download' ? 'Downloading…' : 'Download .md'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
