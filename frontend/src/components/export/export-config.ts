export interface ExportBlock {
  id: string;
  label: string;
  default: boolean;
  meta: string;
}

export interface ExportFormat {
  id: string;
  label: string;
  enabled: boolean;
}

export const EXPORT_BLOCKS: ExportBlock[] = [
  { id: 'transcript', label: 'Raw transcript', default: true, meta: '40 utterances' },
  { id: 'summary', label: 'AI summary', default: true, meta: '2 paragraphs' },
  { id: 'decisions', label: 'Decisions', default: true, meta: '2 items' },
  { id: 'actions', label: 'Action items', default: true, meta: '4 items' },
  { id: 'questions', label: 'Open questions', default: true, meta: '2 items' },
  { id: 'graph', label: 'Knowledge graph (nodes + edges)', default: false, meta: '14 nodes' },
  { id: 'speakers', label: 'Speaker breakdown', default: false, meta: '3 speakers' },
  { id: 'timings', label: 'Word-level timings', default: false, meta: '5 utterances' },
  { id: 'confidence', label: 'Confidence scores', default: false, meta: '' },
];

export const EXPORT_FORMATS: ExportFormat[] = [
  { id: 'md', label: 'Markdown', enabled: true },
  { id: 'pdf', label: 'PDF', enabled: false },
  { id: 'docx', label: 'DOCX', enabled: false },
  { id: 'json', label: 'JSON', enabled: false },
];
