'use client';

import { create } from 'zustand';

export type DrawerDefaults = { filter: 'meeting' | 'all' | 'all-scope'; scope: 'meeting' | 'all' };

interface UIState {
  drawerOpen: boolean;
  drawerDefaults: DrawerDefaults;
  paletteOpen: boolean;
  exportOpen: boolean;
  activeSessionId: string | null;
  setDrawerOpen: (open: boolean) => void;
  toggleDrawer: (defaults?: DrawerDefaults) => void;
  setPaletteOpen: (open: boolean) => void;
  setExportOpen: (open: boolean) => void;
  setActiveSessionId: (id: string | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  drawerOpen: false,
  drawerDefaults: { filter: 'meeting', scope: 'meeting' },
  paletteOpen: false,
  exportOpen: false,
  activeSessionId: null,
  setDrawerOpen: (drawerOpen) => set({ drawerOpen }),
  toggleDrawer: (defaults) =>
    set((s) => ({
      drawerOpen: !s.drawerOpen,
      drawerDefaults: defaults ?? s.drawerDefaults,
    })),
  setPaletteOpen: (paletteOpen) => set({ paletteOpen }),
  setExportOpen: (exportOpen) => set({ exportOpen }),
  setActiveSessionId: (activeSessionId) => set({ activeSessionId }),
}));
