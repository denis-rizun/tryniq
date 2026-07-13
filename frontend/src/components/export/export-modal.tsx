'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Backdrop } from '@/components/ui/backdrop';
import { Checkbox } from '@/components/ui/checkbox';
import { Icon } from '@/components/ui/icon';
import { SectionLabel } from '@/components/ui/section-label';
import { fetchMeetingExport } from '@/lib/api/exports';
import { listMeetings } from '@/lib/api/meetings';
import { cn } from '@/lib/utils';
import type { BlockState } from './build-preview';
import { EXPORT_BLOCKS, EXPORT_FORMATS } from './export-config';

interface ExportModalProps {
  meetingId: string;
  onClose: () => void;
}

const initialBlocks = (): BlockState => {
  const out: BlockState = {};
  EXPORT_BLOCKS.forEach((b) => {
    out[b.id] = b.default;
  });
  return out;
};

export const ExportModal = ({ meetingId, onClose }: ExportModalProps) => {
  const [blocks, setBlocks] = useState<BlockState>(initialBlocks);
  const [format, setFormat] = useState('md');
  const [busy, setBusy] = useState<'download' | 'copy' | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const meetingsQuery = useQuery({ queryKey: ['meetings'], queryFn: listMeetings });
  const meeting = meetingsQuery.data?.find((m) => m.id === meetingId);

  const toggle = (id: string) => setBlocks((b) => ({ ...b, [id]: !b[id] }));
  const allOn = Object.values(blocks).every(Boolean);
  const setAll = (v: boolean) => {
    const out: BlockState = {};
    EXPORT_BLOCKS.forEach((x) => {
      out[x.id] = v;
    });
    setBlocks(out);
  };

  const selectedSections = useMemo(
    () =>
      Object.entries(blocks)
        .filter(([, v]) => v)
        .map(([k]) => k),
    [blocks],
  );

  const previewQuery = useQuery({
    queryKey: ['export-preview', meetingId, selectedSections.join(',')],
    queryFn: async () => {
      const { blob } = await fetchMeetingExport(meetingId, selectedSections);
      return blob.text();
    },
    enabled: format === 'md',
    staleTime: 5_000,
  });

  const onDownload = async () => {
    setBusy('download');
    setError(null);
    try {
      const { blob, filename } = await fetchMeetingExport(meetingId, selectedSections);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename ?? `${meeting?.title || 'meeting'}.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed');
    } finally {
      setBusy(null);
    }
  };

  const onCopy = async () => {
    setBusy('copy');
    setError(null);
    try {
      const { blob } = await fetchMeetingExport(meetingId, selectedSections);
      const text = await blob.text();
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Copy failed');
    } finally {
      setBusy(null);
    }
  };

  useEffect(() => {
    if (previewQuery.error) {
      setError(previewQuery.error instanceof Error ? previewQuery.error.message : 'Preview failed');
    }
  }, [previewQuery.error]);

  const previewText = previewQuery.data ?? (previewQuery.isLoading ? 'Loading…' : '');

  return (
    <>
      <Backdrop onClick={onClose} />
      <div className="modal" style={{ width: 520 }} role="dialog" aria-label="Export meeting">
        <div className="modal-header">
          <SectionLabel>EXPORT MEETING</SectionLabel>
          <div className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
            {meeting ? `${meeting.title} · ${meeting.started_at}` : 'Loading meeting…'}
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
            {previewText}
          </pre>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          {error && (
            <span
              className="mono"
              style={{ fontSize: 11, color: 'var(--color-danger-500)', flex: 1, marginLeft: 8 }}
            >
              {error}
            </span>
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              className="btn"
              onClick={onCopy}
              disabled={busy !== null || format !== 'md'}
            >
              <Icon name="copy" size={12} />{' '}
              {copied ? 'Copied' : busy === 'copy' ? 'Copying…' : 'Copy to clipboard'}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={onDownload}
              disabled={busy !== null || format !== 'md'}
            >
              <Icon name="download" size={12} color="var(--color-paper)" />{' '}
              {busy === 'download' ? 'Downloading…' : 'Download .md'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
