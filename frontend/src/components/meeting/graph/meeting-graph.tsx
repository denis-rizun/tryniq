'use client';

import { useState } from 'react';
import { Icon } from '@/components/ui/icon';
import type { Meeting } from '@/lib/types';
import { EDGES, type GraphNode, NODES } from './graph-data';
import { GraphLegend } from './graph-legend';
import { GraphScrubber } from './graph-scrubber';
import { GraphSidePanel } from './graph-side-panel';
import { GraphSVG } from './graph-svg';

export const MeetingGraph = ({ meeting }: { meeting: Meeting }) => {
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [scrub, setScrub] = useState(1.0);
  const [legendOpen, setLegendOpen] = useState(false);

  const visibleNodes = NODES.filter((n) => n.t <= scrub);
  const visibleIds = new Set(visibleNodes.map((n) => n.id));
  const visibleEdges = EDGES.filter((e) => visibleIds.has(e.from) && visibleIds.has(e.to));

  return (
    <div className="graph-canvas">
      <div style={{ padding: '14px 24px 0', display: 'flex', alignItems: 'center', gap: 12 }}>
        <span className="section-label" style={{ marginBottom: 0 }}>
          GRAPH
        </span>
        <span
          className="filter-chip mono"
          style={{ cursor: 'pointer' }}
          onClick={() => setLegendOpen((o) => !o)}
        >
          legend {legendOpen ? '▾' : '▸'}
        </span>
      </div>

      {legendOpen && <GraphLegend />}

      <div className="graph-toolbar">
        <button type="button" title="zoom in">
          <Icon name="zoom-in" size={14} />
        </button>
        <button type="button" title="zoom out">
          <Icon name="zoom-out" size={14} />
        </button>
        <button type="button" title="fit">
          <Icon name="fit" size={14} />
        </button>
        <button type="button" title="reset layout">
          <Icon name="reset" size={14} />
        </button>
      </div>

      <GraphSVG
        visibleNodes={visibleNodes}
        visibleEdges={visibleEdges}
        selected={selected}
        onSelect={setSelected}
      />

      {selected && <GraphSidePanel node={selected} onClose={() => setSelected(null)} />}

      <GraphScrubber
        scrub={scrub}
        setScrub={setScrub}
        durationLabel={meeting.durationLive ?? '—'}
      />
    </div>
  );
};
