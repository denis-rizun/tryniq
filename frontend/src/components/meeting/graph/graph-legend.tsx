import { colorFor, type NodeKind } from './graph-data';

const ITEMS: [NodeKind, string][] = [
  ['decision', 'decision'],
  ['action', 'action item'],
  ['question', 'open question'],
  ['entity', 'person'],
  ['topic', 'topic'],
  ['meeting', 'meeting'],
];

export const GraphLegend = () => (
  <div
    className="graph-legend"
    style={{
      background: 'var(--color-paper-lift)',
      border: '1px solid var(--color-border)',
      borderRadius: 4,
      padding: '8px 10px',
      top: 56,
    }}
  >
    <div
      className="mono"
      style={{ fontSize: 10, color: 'var(--color-ink-tertiary)', marginBottom: 4 }}
    >
      NODE TYPES
    </div>
    {ITEMS.map(([k, l]) => (
      <div key={k} className="legend-item">
        <span className="legend-swatch" style={{ background: colorFor(k) }} />
        {l}
      </div>
    ))}
  </div>
);
