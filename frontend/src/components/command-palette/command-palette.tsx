'use client';

import { useEffect, useRef, useState } from 'react';
import { Avatar } from '@/components/ui/avatar';
import { Backdrop } from '@/components/ui/backdrop';
import { SectionLabel } from '@/components/ui/section-label';
import { StatusDot } from '@/components/ui/status-dot';
import { cn } from '@/lib/utils';
import type { CommandPaletteProps, PaletteAction, PaletteItem } from './types';

const BASE_ACTIONS: PaletteAction[] = [
  { id: 'new', label: 'New meeting', kbd: 'N' },
  { id: 'upload', label: 'Upload recording', kbd: 'U' },
  { id: 'ai', label: 'Open AI assistant', kbd: '⌘L' },
];

const matches = (text: string, q: string) => !q || text.toLowerCase().includes(q.toLowerCase());

export const CommandPalette = ({
  open,
  onClose,
  onAction,
  meetings,
  people,
}: CommandPaletteProps) => {
  const [q, setQ] = useState('');
  const [idx, setIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (open) {
      setQ('');
      setIdx(0);
    }
  }, [open]);

  if (!open) return null;

  const recent = meetings.slice(0, 4).filter((m) => matches(m.title, q));
  const peopleList = Object.values(people)
    .filter((p) => matches(p.name, q))
    .slice(0, 4);
  const actions = BASE_ACTIONS.filter((a) => matches(a.label, q));
  const askRow: PaletteAction[] = q.trim()
    ? [{ id: 'ask', label: `Ask AI: "${q}"`, kbd: '↵', isAsk: true }]
    : [];

  const all: PaletteItem[] = [
    ...recent.map((m) => ({ ...m, _kind: 'meeting' as const })),
    ...peopleList.map((p) => ({ ...p, _kind: 'person' as const })),
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

  let cursor = 0;
  return (
    <>
      <Backdrop onClick={onClose} />
      <div className="modal cmd-modal" role="dialog" aria-label="Command palette">
        <input
          ref={inputRef}
          className="cmd-input"
          placeholder="Search meetings, people, actions… or ask AI"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setIdx(0);
          }}
          onKeyDown={onKey}
        />
        <div className="cmd-list">
          {recent.length > 0 && (
            <>
              <div style={{ marginTop: 6 }}>
                <SectionLabel>RECENT MEETINGS</SectionLabel>
              </div>
              {recent.map((m) => {
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
          {peopleList.length > 0 && (
            <>
              <div style={{ marginTop: 14 }}>
                <SectionLabel>PEOPLE</SectionLabel>
              </div>
              {peopleList.map((p) => {
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
