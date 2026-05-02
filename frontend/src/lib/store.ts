'use client';

import { create } from 'zustand';
import { sessions as initialSessions } from '@/lib/mock';
import type { ChatSession } from '@/lib/types';

export type DrawerDefaults = { filter: 'meeting' | 'all' | 'all-scope'; scope: 'meeting' | 'all' };

interface UIState {
  drawerOpen: boolean;
  drawerDefaults: DrawerDefaults;
  paletteOpen: boolean;
  exportOpen: boolean;
  sessions: ChatSession[];
  activeSessionId: string;
  setDrawerOpen: (open: boolean) => void;
  toggleDrawer: (defaults?: DrawerDefaults) => void;
  setPaletteOpen: (open: boolean) => void;
  setExportOpen: (open: boolean) => void;
  setSessions: (next: ChatSession[] | ((prev: ChatSession[]) => ChatSession[])) => void;
  setActiveSessionId: (id: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  drawerOpen: false,
  drawerDefaults: { filter: 'meeting', scope: 'meeting' },
  paletteOpen: false,
  exportOpen: false,
  sessions: initialSessions,
  activeSessionId: initialSessions[0].id,
  setDrawerOpen: (drawerOpen) => set({ drawerOpen }),
  toggleDrawer: (defaults) =>
    set((s) => ({
      drawerOpen: !s.drawerOpen,
      drawerDefaults: defaults ?? s.drawerDefaults,
    })),
  setPaletteOpen: (paletteOpen) => set({ paletteOpen }),
  setExportOpen: (exportOpen) => set({ exportOpen }),
  setSessions: (next) =>
    set((s) => ({ sessions: typeof next === 'function' ? next(s.sessions) : next })),
  setActiveSessionId: (activeSessionId) => set({ activeSessionId }),
}));
