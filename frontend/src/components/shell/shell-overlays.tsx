'use client';

import { useRouter } from 'next/navigation';
import { AIAssistantDrawer } from '@/components/chat/ai-drawer';
import { CommandPalette } from '@/components/command-palette/command-palette';
import { ExportModal } from '@/components/export/export-modal';
import { useKeyboardShortcuts } from '@/lib/hooks/use-keyboard-shortcuts';
import { useUIStore } from '@/lib/store';

export const ShellOverlays = () => {
  useKeyboardShortcuts();
  const router = useRouter();
  const {
    drawerOpen,
    drawerDefaults,
    setDrawerOpen,
    paletteOpen,
    setPaletteOpen,
    exportOpen,
    exportMeetingId,
    setExportOpen,
    toggleDrawer,
  } = useUIStore();

  return (
    <>
      <AIAssistantDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        defaultFilter={drawerDefaults.filter}
        defaultScope={drawerDefaults.scope}
      />
      {exportOpen && exportMeetingId && (
        <ExportModal meetingId={exportMeetingId} onClose={() => setExportOpen(false)} />
      )}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onAction={(item) => {
          setPaletteOpen(false);
          if (item._kind === 'meeting') router.push(`/meetings/${item.id}/overview`);
          else if (item._kind === 'person') router.push('/people');
          else if (item._kind === 'utterance') {
            router.push(`/meetings/${item.meetingId}/overview?cite=${item.tStart}`);
          } else if (item._kind === 'action') {
            if (item.id === 'new') router.push('/');
            else if (item.id === 'upload') router.push('/upload');
            else if (item.id === 'ai' || item.id === 'ask') toggleDrawer();
          }
        }}
      />
    </>
  );
};
