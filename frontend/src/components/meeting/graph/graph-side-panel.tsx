import { Icon } from '@/components/ui/icon';
import type { GraphNode } from './graph-data';

const sourceTimeFor = (kind: GraphNode['kind']): string =>
  kind === 'decision' ? '02:31' : kind === 'action' ? '02:47' : kind === 'question' ? '03:12' : '—';

interface GraphSidePanelProps {
  node: GraphNode;
  onClose: () => void;
}

export const GraphSidePanel = ({ node, onClose }: GraphSidePanelProps) => (
  <div className="graph-side-panel">
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
      }}
    >
      <span className="section-label" style={{ marginBottom: 0 }}>
        {node.kind.toUpperCase()}
      </span>
      <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
        <Icon name="x" size={12} />
      </button>
    </div>
    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{node.label}</div>
    <div
      className="mono"
      style={{ fontSize: 11, color: 'var(--color-ink-secondary)', marginBottom: 12 }}
    >
      status: {node.status}
      {node.ownerless ? ' · no owner' : ''}
    </div>
    <div style={{ fontSize: 12, color: 'var(--color-ink-secondary)', marginBottom: 12 }}>
      Source: utterance at {sourceTimeFor(node.kind)}
    </div>
    <button type="button" className="btn btn-sm" style={{ width: '100%' }}>
      Edit
    </button>
  </div>
);
