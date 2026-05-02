'use client';

import { useEffect, useRef, useState } from 'react';
import type { Scope } from '@/components/chat/scope-toggle';
import { useUIStore } from '@/lib/store';
import type { ChatSession } from '@/lib/types';

type Filter = 'meeting' | 'all' | 'all-scope';

const replyFor = (scope: Scope): string =>
  scope === 'meeting'
    ? 'Based on the current meeting, the team agreed to roll back the eu-west-1 deploy and investigate the migration script. [02:31] Mike Torres took ownership of both the script investigation and pulling the CI history. [02:47]'
    : "Across your meetings, the most recent reference is from this morning's deploy debrief. The auth refactor was last discussed in detail on Apr 17 in the design review. [Apr 17 · 12:14]";

export const useAIDrawer = (open: boolean, defaultFilter: Filter, defaultScope: Scope) => {
  const { sessions, setSessions, activeSessionId, setActiveSessionId } = useUIStore();
  const [filter, setFilter] = useState<Filter>(defaultFilter);
  const [scope, setScope] = useState<Scope>(defaultScope);
  const [scopeChanged, setScopeChanged] = useState(false);
  const [draft, setDraft] = useState('');
  const [streamingMsg, setStreamingMsg] = useState<{ id: string } | null>(null);
  const msgsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (open) {
      setFilter(defaultFilter);
      setScope(defaultScope);
      setScopeChanged(false);
    }
  }, [open, defaultFilter, defaultScope]);

  const active = sessions.find((s) => s.id === activeSessionId) ?? sessions[0];

  const filteredSessions = sessions.filter((s) => {
    if (filter === 'meeting') return s.scope === 'meeting';
    if (filter === 'all-scope') return s.scope === 'all';
    return true;
  });

  const messageCount = active?.messages.length ?? 0;
  useEffect(() => {
    void messageCount;
    void streamingMsg;
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
  }, [messageCount, streamingMsg]);

  const handleScopeChange = (next: Scope) => {
    if (next !== scope && active && active.messages.length > 0) setScopeChanged(true);
    setScope(next);
  };

  const newSession = () => {
    const id = `s_${Math.random().toString(36).slice(2, 7)}`;
    const fresh: ChatSession = {
      id,
      title: scope === 'meeting' ? 'Production deploy debrief' : 'All meetings',
      meetingId: scope === 'meeting' ? 'm_demo' : null,
      scope,
      isActive: true,
      relTime: 'just now',
      messages: [],
    };
    setSessions([fresh, ...sessions.map((x) => ({ ...x, isActive: false }))]);
    setActiveSessionId(id);
    setScopeChanged(false);
  };

  const send = () => {
    if (!draft.trim() || !active) return;
    const userMsg = { role: 'user' as const, text: draft.trim() };
    setSessions((curr) =>
      curr.map((s) => (s.id === active.id ? { ...s, messages: [...s.messages, userMsg] } : s)),
    );
    setDraft('');
    setTimeout(() => {
      const asst = {
        role: 'asst' as const,
        text: replyFor(scope),
        model: 'claude-haiku-4.5',
        sources: 2,
        latency: '1.1s',
        _animate: true,
      };
      setStreamingMsg({ id: active.id });
      setSessions((curr) =>
        curr.map((s) => (s.id === active.id ? { ...s, messages: [...s.messages, asst] } : s)),
      );
      setTimeout(() => setStreamingMsg(null), 1500);
    }, 350);
  };

  return {
    sessions: filteredSessions,
    active,
    filter,
    setFilter,
    scope,
    handleScopeChange,
    scopeChanged,
    draft,
    setDraft,
    streamingMsg,
    msgsRef,
    newSession,
    send,
    setActiveSessionId,
  };
};
