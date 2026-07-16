'use client';

import { useEffect, useRef, useState } from 'react';
import { Backdrop } from '@/components/ui/backdrop';
import { SectionLabel } from '@/components/ui/section-label';
import { usePaletteSearch } from '@/lib/hooks/use-palette-search';
import { PaletteResultRow } from './palette-result-row';
import type { CommandPaletteProps, PaletteItem } from './types';

export const CommandPalette = ({ open, onClose, onAction }: CommandPaletteProps) => {
  const [idx, setIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const {
    actions,
    askRow,
    debouncedQuery,
    meetings,
    people,
    query,
    searchQuery,
    setQuery,
    utterances,
  } = usePaletteSearch(open);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      setIdx(0);
    }
  }, [open]);

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
    debouncedQuery.length > 0 &&
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
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIdx(0);
          }}
          onKeyDown={onKey}
        />
        <div className="cmd-list">
          {searchQuery.isFetching && debouncedQuery && (
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
                  <PaletteResultRow
                    key={m.id}
                    active={idx === ci}
                    item={{ ...m, _kind: 'meeting' }}
                    onAction={onAction}
                    onHover={() => setIdx(ci)}
                  />
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
                  <PaletteResultRow
                    key={p.id}
                    active={idx === ci}
                    item={{ ...p, _kind: 'person' }}
                    onAction={onAction}
                    onHover={() => setIdx(ci)}
                  />
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
                return (
                  <PaletteResultRow
                    key={u.id}
                    active={idx === ci}
                    item={{ ...u, _kind: 'utterance' }}
                    onAction={onAction}
                    onHover={() => setIdx(ci)}
                  />
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
                  <PaletteResultRow
                    key={a.id}
                    active={idx === ci}
                    item={{ ...a, _kind: 'action' }}
                    onAction={onAction}
                    onHover={() => setIdx(ci)}
                  />
                );
              })}
            </>
          )}
        </div>
      </div>
    </>
  );
};
