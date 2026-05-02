import type { MeetingListItem, PeopleMap, Person } from '@/lib/types';

export interface PaletteAction {
  id: string;
  label: string;
  kbd?: string;
  isAsk?: boolean;
}

export type PaletteItem =
  | (MeetingListItem & { _kind: 'meeting' })
  | (Person & { _kind: 'person' })
  | (PaletteAction & { _kind: 'action' });

export interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onAction: (item: PaletteItem) => void;
  meetings: MeetingListItem[];
  people: PeopleMap;
}
