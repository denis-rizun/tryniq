'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Icon } from '@/components/ui/icon';
import { useGraphSimulation } from '@/lib/hooks/use-graph-simulation';
import { useMeetingGraph } from '@/lib/hooks/use-meeting-graph';
import type { Meeting } from '@/lib/types';
import { GraphCanvas } from './graph-canvas';
import type { GraphNode } from './graph-data';
import { GraphLegend } from './graph-legend';
import { GraphScrubber } from './graph-scrubber';
import { GraphSidePanel } from './graph-side-panel';
import { tidyLayout } from './tidy-layout';

const useElementSize = (): [
  React.RefObject<HTMLDivElement | null>,
  { width: number; height: number },
] => {
  const ref = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ width: 800, height: 520 });
  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0]?.contentRect;
      if (!r) return;
      setSize({ width: Math.max(320, r.width), height: Math.max(320, r.height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, size];
};

export const MeetingGraph = ({ meeting }: { meeting: Meeting }) => {
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [scrub, setScrub] = useState(1.0);
  const [playing, setPlaying] = useState(false);
  const [legendOpen, setLegendOpen] = useState(false);
  const { nodes, edges, isLoading } = useMeetingGraph(meeting.id);
  const [containerRef, size] = useElementSize();

  const visibleNodes = useMemo(() => nodes.filter((n) => n.t <= scrub + 1e-6), [nodes, scrub]);
  const visibleIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);
  const visibleEdges = useMemo(
    () => edges.filter((e) => visibleIds.has(e.from) && visibleIds.has(e.to)),
    [edges, visibleIds],
  );

  const canvasWidth = size.width;
  const canvasHeight = size.height - 100;
  const sim = useGraphSimulation(visibleNodes, visibleEdges, canvasWidth, canvasHeight);

  const onTidyClick = () => {
    const positions = tidyLayout(visibleNodes, visibleEdges, {
      cx: canvasWidth / 2,
      cy: canvasHeight / 2,
      width: canvasWidth,
      height: canvasHeight,
    });
    sim.tidy(positions);
  };

  return (
    <div className="graph-canvas" ref={containerRef}>
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
        {isLoading && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
            loading…
          </span>
        )}
        {!isLoading && nodes.length === 0 && (
          <span className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
            no graph yet — runs after meeting end
          </span>
        )}
      </div>

      {legendOpen && <GraphLegend />}

      <div className="graph-toolbar">
        <button type="button" title="reset view">
          <Icon name="reset" size={14} />
        </button>
        <button type="button" title="tidy layout" onClick={onTidyClick}>
          <Icon name="tidy" size={14} />
        </button>
      </div>

      <div style={{ position: 'absolute', inset: '40px 0 60px 0' }}>
        <GraphCanvas
          nodes={visibleNodes}
          edges={visibleEdges}
          simNodes={sim.nodes}
          simLinks={sim.links}
          pin={sim.pin}
          selected={selected}
          onSelect={setSelected}
          width={canvasWidth}
          height={canvasHeight}
        />
      </div>

      {selected && <GraphSidePanel node={selected} onClose={() => setSelected(null)} />}

      <GraphScrubber
        scrub={scrub}
        setScrub={setScrub}
        durationLabel={meeting.durationLive ?? meeting.duration ?? '—'}
        playing={playing}
        setPlaying={setPlaying}
      />
    </div>
  );
};
