'use client';

import { useMemo, useState } from 'react';
import { Backdrop } from '@/components/ui/backdrop';
import { Checkbox } from '@/components/ui/checkbox';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import type { Meeting } from '@/lib/types';
import { cn } from '@/lib/utils';
import { type BlockState, buildPreview } from './build-preview';
import { EXPORT_BLOCKS, EXPORT_FORMATS } from './export-config';

interface ExportModalProps {
  meeting: Meeting;
  onClose: () => void;
}

const initialBlocks = (): BlockState => {
  const out: BlockState = {};
  EXPORT_BLOCKS.forEach((b) => {
    out[b.id] = b.default;
  });
  return out;
};

export const ExportModal = ({ meeting, onClose }: ExportModalProps) => {
  const [blocks, setBlocks] = useState<BlockState>(initialBlocks);
  const [format, setFormat] = useState('md');

  const toggle = (id: string) => setBlocks((b) => ({ ...b, [id]: !b[id] }));
  const allOn = Object.values(blocks).every(Boolean);
  const setAll = (v: boolean) => {
    const out: BlockState = {};
    EXPORT_BLOCKS.forEach((x) => {
      out[x.id] = v;
    });
    setBlocks(out);
  };

  const preview = useMemo(() => buildPreview(meeting, blocks), [blocks, meeting]);

  return (
    <>
      <Backdrop onClick={onClose} />
      <div className="modal" style={{ width: 520 }} role="dialog" aria-label="Export meeting">
        <div className="modal-header">
          <SectionLabel>EXPORT MEETING</SectionLabel>
          <div className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
            {meeting.title} · {meeting.startedAt}
          </div>
        </div>
        <div className="modal-body">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 8,
            }}
          >
            <SectionLabel>INCLUDE</SectionLabel>
            <span
              className="mono"
              style={{ fontSize: 11, color: 'var(--color-accent-500)', cursor: 'pointer' }}
              onClick={() => setAll(!allOn)}
            >
              {allOn ? 'Select none' : 'Select all'}
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 18 }}>
            {EXPORT_BLOCKS.map((b) => (
              <label
                key={b.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  cursor: 'pointer',
                  padding: '4px 0',
                }}
              >
                <Checkbox checked={blocks[b.id]} onChange={() => toggle(b.id)} />
                <span style={{ fontSize: 13, flex: 1 }}>{b.label}</span>
                {b.meta && (
                  <span
                    className="mono"
                    style={{ fontSize: 11, color: 'var(--color-ink-tertiary)' }}
                  >
                    ({b.meta})
                  </span>
                )}
              </label>
            ))}
          </div>

          <SectionLabel>FORMAT</SectionLabel>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
            {EXPORT_FORMATS.map((f) => (
              <button
                key={f.id}
                type="button"
                className={cn('format-pill', !f.enabled && 'disabled', format === f.id && 'active')}
                onClick={() => f.enabled && setFormat(f.id)}
              >
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: format === f.id ? 'var(--color-accent-500)' : 'transparent',
                    border: format === f.id ? 'none' : '1px solid var(--color-ink-tertiary)',
                  }}
                />
                {f.label}
                {!f.enabled && <span style={{ marginLeft: 4 }}>(soon)</span>}
              </button>
            ))}
          </div>

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
            {preview}
          </pre>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="btn">
              <Icon name="copy" size={12} /> Copy to clipboard
            </button>
            <button type="button" className="btn btn-primary">
              <Icon name="download" size={12} color="var(--color-paper)" /> Download .md
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
