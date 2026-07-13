'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Avatar } from '@/components/ui/avatar';
import { Backdrop } from '@/components/ui/backdrop';
import { SectionLabel } from '@/components/ui/section-label';
import { StatusDot } from '@/components/ui/status-dot';
import { searchAll } from '@/lib/api/search';
import { formatTimestamp } from '@/lib/format';
import { cn } from '@/lib/utils';
import type {
  CommandPaletteProps,
  PaletteAction,
  PaletteItem,
  PaletteMeeting,
  PalettePerson,
  PaletteUtterance,
} from './types';

const BASE_ACTIONS: PaletteAction[] = [
  { id: 'new', label: 'New meeting', kbd: 'N' },
  { id: 'upload', label: 'Upload recording', kbd: 'U' },
  { id: 'ai', label: 'Open AI assistant', kbd: '⌘L' },
];

const PALETTE_AVATAR_COLORS = ['#A6B58F', '#C9A87A', '#B89AA5', '#9DA9B8', '#9C82A6', '#8FA6B5'];

const initialsOf = (name: string): string => {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

const colorFor = (id: string): string => {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return PALETTE_AVATAR_COLORS[h % PALETTE_AVATAR_COLORS.length];
};

const formatRelative = (iso: string): string => {
  const ms = new Date(iso).getTime();
  if (Number.isNaN(ms)) return iso;
  const diffSec = Math.max(0, (Date.now() - ms) / 1000);
  if (diffSec < 60) return 'just now';
  const m = Math.floor(diffSec / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
};

const stateOf = (status: string): 'live' | 'finalizing' | 'final' => {
  if (status === 'live') return 'live';
  if (status === 'final' || status === 'failed') return 'final';
  return 'finalizing';
};

export const CommandPalette = ({ open, onClose, onAction }: CommandPaletteProps) => {
  const [q, setQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [idx, setIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      setQ('');
      setDebouncedQ('');
      setIdx(0);
    }
  }, [open]);

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedQ(q.trim()), 150);
    return () => clearTimeout(handle);
  }, [q]);

  const searchQuery = useQuery({
    queryKey: ['palette-search', debouncedQ],
    queryFn: () => searchAll(debouncedQ),
    enabled: open && debouncedQ.length > 0,
    staleTime: 5_000,
  });

  const meetings: PaletteMeeting[] = useMemo(
    () =>
      (searchQuery.data?.results.meetings ?? []).map((m) => ({
        id: m.id,
        title: m.title,
        state: stateOf(m.status),
        relativeStart: formatRelative(m.started_at),
      })),
    [searchQuery.data],
  );
  const people: PalettePerson[] = useMemo(
    () =>
      (searchQuery.data?.results.people ?? []).map((p) => ({
        id: p.id,
        name: p.name,
        initials: initialsOf(p.name),
        color: colorFor(p.id),
      })),
    [searchQuery.data],
  );
  const utterances: PaletteUtterance[] = useMemo(
    () =>
      (searchQuery.data?.results.utterances ?? []).map((u) => ({
        id: u.id,
        meetingId: u.meeting_id,
        meetingTitle: u.meeting_title,
        participantName: u.speaker_name,
        tStart: u.t_start,
        text: u.text,
      })),
    [searchQuery.data],
  );

  const actions = BASE_ACTIONS.filter((a) => !q || a.label.toLowerCase().includes(q.toLowerCase()));
  const askRow: PaletteAction[] = q.trim()
    ? [{ id: 'ask', label: `Ask AI: "${q}"`, kbd: '↵', isAsk: true }]
    : [];

  if (!open) return null;

  const all: PaletteItem[] = [
    ...meetings.map((m) => ({ ...m, _kind: 'meeting' as const })),
    ...people.map((p) => ({ ...p, _kind: 'person' as const })),
    ...utterances.map((u) => ({ ...u, _kind: 'utterance' as const })),
    ...actions.map((a) => ({ ...a, _kind: 'action' as const })),
    ...askRow.map((a) => ({ ...a, _kind: 'action' as const })),
  ];

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setIdx((i) => Math.min(i + 1, all.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const it = all[idx];
      if (it) onAction(it);
    }
  };

  const empty =
    debouncedQ.length > 0 &&
    !searchQuery.isFetching &&
    meetings.length === 0 &&
    people.length === 0 &&
    utterances.length === 0;

  let cursor = 0;
  return (
    <>
      <Backdrop onClick={onClose} />
      <div className="modal cmd-modal" role="dialog" aria-label="Command palette">
        <input
          ref={inputRef}
          className="cmd-input"
          placeholder="Search meetings, people, transcripts… or ask AI"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setIdx(0);
          }}
          onKeyDown={onKey}
        />
        <div className="cmd-list">
          {searchQuery.isFetching && debouncedQ && (
            <div style={{ padding: '8px 4px', fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
              Searching…
            </div>
          )}
          {meetings.length > 0 && (
            <>
              <div style={{ marginTop: 6 }}>
                <SectionLabel>MEETINGS</SectionLabel>
              </div>
              {meetings.map((m) => {
                const ci = cursor++;
                return (
                  <div
                    key={m.id}
                    className={cn('cmd-row', idx === ci && 'active')}
                    onMouseEnter={() => setIdx(ci)}
                    onClick={() => onAction({ ...m, _kind: 'meeting' })}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <StatusDot kind={m.state === 'live' ? 'live' : 'final'} />
                      {m.title}
                    </div>
                    <span className="right">{m.relativeStart}</span>
                  </div>
                );
              })}
            </>
          )}
          {people.length > 0 && (
            <>
              <div style={{ marginTop: 14 }}>
                <SectionLabel>PEOPLE</SectionLabel>
              </div>
              {people.map((p) => {
                const ci = cursor++;
                return (
                  <div
                    key={p.id}
                    className={cn('cmd-row', idx === ci && 'active')}
                    onMouseEnter={() => setIdx(ci)}
                    onClick={() => onAction({ ...p, _kind: 'person' })}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Avatar person={p} />
                      {p.name}
                    </div>
                    <span className="right">person</span>
                  </div>
                );
              })}
            </>
          )}
          {utterances.length > 0 && (
            <>
              <div style={{ marginTop: 14 }}>
                <SectionLabel>TRANSCRIPTS</SectionLabel>
              </div>
              {utterances.map((u) => {
                const ci = cursor++;
                const speaker = u.participantName ?? 'Speaker';
                return (
                  <div
                    key={u.id}
                    className={cn('cmd-row', idx === ci && 'active')}
                    onMouseEnter={() => setIdx(ci)}
                    onClick={() => onAction({ ...u, _kind: 'utterance' })}
                  >
                    <div
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 2,
                        minWidth: 0,
                        flex: 1,
                      }}
                    >
                      <div
                        style={{
                          fontSize: 13,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {u.text}
                      </div>
                      <div
                        className="mono"
                        style={{ fontSize: 10, color: 'var(--color-ink-tertiary)' }}
                      >
                        {speaker} · {u.meetingTitle}
                      </div>
                    </div>
                    <span className="right mono">{formatTimestamp(u.tStart)}</span>
                  </div>
                );
              })}
            </>
          )}
          {empty && (
            <div style={{ padding: '8px 4px', fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
              No matches.
            </div>
          )}
          {(actions.length > 0 || askRow.length > 0) && (
            <>
              <div style={{ marginTop: 14 }}>
                <SectionLabel>ACTIONS</SectionLabel>
              </div>
              {[...actions, ...askRow].map((a) => {
                const ci = cursor++;
                return (
                  <div
                    key={a.id}
                    className={cn('cmd-row', idx === ci && 'active')}
                    onMouseEnter={() => setIdx(ci)}
                    onClick={() => onAction({ ...a, _kind: 'action' })}
                  >
                    <div style={{ color: a.isAsk ? 'var(--color-accent-500)' : 'inherit' }}>
                      {a.label}
                    </div>
                    <span className="right">{a.kbd}</span>
                  </div>
                );
              })}
            </>
          )}
        </div>
      </div>
    </>
  );
};
