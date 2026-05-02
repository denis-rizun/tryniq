'use client';

import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { useUIStore } from '@/lib/store';

const isFormElement = (el: Element | null): boolean =>
  el?.tagName === 'INPUT' || el?.tagName === 'TEXTAREA';

export const useKeyboardShortcuts = () => {
  const {
    setPaletteOpen,
    setExportOpen,
    setDrawerOpen,
    toggleDrawer,
    paletteOpen,
    exportOpen,
    drawerOpen,
  } = useUIStore();
  const pathname = usePathname();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey;
      const key = e.key.toLowerCase();
      if (meta && key === 'k') {
        e.preventDefault();
        setPaletteOpen(!paletteOpen);
      } else if (meta && key === 'j') {
        e.preventDefault();
        toggleDrawer();
      } else if (meta && key === 'e' && pathname.startsWith('/meetings/')) {
        e.preventDefault();
        setExportOpen(true);
      } else if (e.key === 'Escape') {
        if (paletteOpen) setPaletteOpen(false);
        else if (exportOpen) setExportOpen(false);
        else if (drawerOpen) setDrawerOpen(false);
      } else if (
        e.key === '/' &&
        pathname === '/meetings' &&
        !isFormElement(document.activeElement)
      ) {
        e.preventDefault();
        document.querySelector<HTMLInputElement>('.input')?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [
    paletteOpen,
    exportOpen,
    drawerOpen,
    pathname,
    setPaletteOpen,
    setExportOpen,
    setDrawerOpen,
    toggleDrawer,
  ]);
};
