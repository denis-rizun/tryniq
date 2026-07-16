import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { fetchMeetingExport } from '@/lib/api/exports';
import { listMeetings } from '@/lib/api/meetings';
import type { BlockState } from './build-preview';
import { EXPORT_BLOCKS } from './export-config';

const initialBlocks = (): BlockState =>
  Object.fromEntries(EXPORT_BLOCKS.map((block) => [block.id, block.default]));

export const useMeetingExport = (meetingId: string) => {
  const [blocks, setBlocks] = useState<BlockState>(initialBlocks);
  const [format, setFormat] = useState('md');
  const [busy, setBusy] = useState<'download' | 'copy' | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const meetingsQuery = useQuery({ queryKey: ['meetings'], queryFn: listMeetings });
  const meeting = meetingsQuery.data?.find((item) => item.id === meetingId);
  const selectedSections = useMemo(
    () =>
      Object.entries(blocks)
        .filter(([, selected]) => selected)
        .map(([id]) => id),
    [blocks],
  );
  const previewQuery = useQuery({
    queryKey: ['export-preview', meetingId, selectedSections.join(',')],
    queryFn: async () => (await fetchMeetingExport(meetingId, selectedSections)).blob.text(),
    enabled: format === 'md',
    staleTime: 5_000,
  });
  useEffect(() => {
    if (previewQuery.error)
      setError(previewQuery.error instanceof Error ? previewQuery.error.message : 'Preview failed');
  }, [previewQuery.error]);
  const download = async () => {
    setBusy('download');
    setError(null);
    try {
      const { blob, filename } = await fetchMeetingExport(meetingId, selectedSections);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename ?? `${meeting?.title || 'meeting'}.md`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Export failed');
    } finally {
      setBusy(null);
    }
  };
  const copy = async () => {
    setBusy('copy');
    setError(null);
    try {
      const { blob } = await fetchMeetingExport(meetingId, selectedSections);
      await navigator.clipboard.writeText(await blob.text());
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Copy failed');
    } finally {
      setBusy(null);
    }
  };
  const toggle = (id: string) => setBlocks((current) => ({ ...current, [id]: !current[id] }));
  const allOn = Object.values(blocks).every(Boolean);
  const toggleAll = () =>
    setBlocks(Object.fromEntries(EXPORT_BLOCKS.map((block) => [block.id, !allOn])));
  return {
    allOn,
    blocks,
    busy,
    copied,
    copy,
    download,
    error,
    format,
    meeting,
    preview: previewQuery.data ?? (previewQuery.isLoading ? 'Loading…' : ''),
    setFormat,
    toggle,
    toggleAll,
  };
};
