export interface PaletteAction {
  id: string;
  label: string;
  kbd?: string;
  isAsk?: boolean;
}

export interface PaletteMeeting {
  id: string;
  title: string;
  state: 'live' | 'finalizing' | 'final';
  relativeStart: string;
}

export interface PalettePerson {
  id: string;
  name: string;
  initials: string;
  color: string;
}

export interface PaletteUtterance {
  id: string;
  meetingId: string;
  meetingTitle: string;
  participantName: string | null;
  tStart: number;
  text: string;
}

export type PaletteItem =
  | (PaletteMeeting & { _kind: 'meeting' })
  | (PalettePerson & { _kind: 'person' })
  | (PaletteUtterance & { _kind: 'utterance' })
  | (PaletteAction & { _kind: 'action' });

export interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onAction: (item: PaletteItem) => void;
}
