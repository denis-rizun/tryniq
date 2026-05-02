export interface Stage {
  label: string;
  detail: string;
}

export const STAGES: Stage[] = [
  { label: 'Uploading', detail: '14.2 MB / 24.8 MB' },
  { label: 'Separating speakers', detail: 'diarization' },
  { label: 'Transcribing', detail: '14:23 / 32:00' },
  { label: 'Generating notes', detail: 'claude-haiku-4.5' },
  { label: 'Building graph', detail: 'topics, decisions, actions' },
  { label: 'Done', detail: 'ready' },
];
