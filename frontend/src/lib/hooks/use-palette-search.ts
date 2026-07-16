'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import type {
  PaletteAction,
  PaletteMeeting,
  PalettePerson,
  PaletteUtterance,
} from '@/components/command-palette/types';
import { searchAll } from '@/lib/api/search';
import { colorForId, formatRelativeShort, initialsOf } from '@/lib/format';

const baseActions: PaletteAction[] = [
  { id: 'new', label: 'New meeting', kbd: 'N' },
  { id: 'upload', label: 'Upload recording', kbd: 'U' },
  { id: 'ai', label: 'Open AI assistant', kbd: '⌘L' },
];

const stateOf = (status: string): 'live' | 'finalizing' | 'final' =>
  status === 'live' ? 'live' : status === 'final' || status === 'failed' ? 'final' : 'finalizing';

export const usePaletteSearch = (open: boolean) => {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  useEffect(() => {
    if (open) {
      setQuery('');
      setDebouncedQuery('');
    }
  }, [open]);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query.trim()), 150);
    return () => clearTimeout(timer);
  }, [query]);
  const searchQuery = useQuery({
    queryKey: ['palette-search', debouncedQuery],
    queryFn: () => searchAll(debouncedQuery),
    enabled: open && Boolean(debouncedQuery),
    staleTime: 5_000,
  });
  const meetings = useMemo<PaletteMeeting[]>(
    () =>
      (searchQuery.data?.results.meetings ?? []).map((meeting) => ({
        id: meeting.id,
        title: meeting.title,
        state: stateOf(meeting.status),
        relativeStart: formatRelativeShort(meeting.started_at),
      })),
    [searchQuery.data],
  );
  const people = useMemo<PalettePerson[]>(
    () =>
      (searchQuery.data?.results.people ?? []).map((person) => ({
        id: person.id,
        name: person.name,
        initials: initialsOf(person.name),
        color: colorForId(person.id),
      })),
    [searchQuery.data],
  );
  const utterances = useMemo<PaletteUtterance[]>(
    () =>
      (searchQuery.data?.results.utterances ?? []).map((utterance) => ({
        id: utterance.id,
        meetingId: utterance.meeting_id,
        meetingTitle: utterance.meeting_title,
        participantName: utterance.speaker_name,
        tStart: utterance.t_start,
        text: utterance.text,
      })),
    [searchQuery.data],
  );
  const actions = baseActions.filter(
    (action) => !query || action.label.toLowerCase().includes(query.toLowerCase()),
  );
  const askRow: PaletteAction[] = query.trim()
    ? [{ id: 'ask', label: `Ask AI: "${query}"`, kbd: '↵', isAsk: true }]
    : [];
  return {
    actions,
    askRow,
    debouncedQuery,
    meetings,
    people,
    query,
    searchQuery,
    setQuery,
    utterances,
  };
};
