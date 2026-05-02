interface GraphScrubberProps {
  scrub: number;
  setScrub: (n: number) => void;
  durationLabel: string;
}

export const GraphScrubber = ({ scrub, setScrub, durationLabel }: GraphScrubberProps) => (
  <div className="scrubber">
    <span className="mono" style={{ fontSize: 10, color: 'var(--color-ink-tertiary)' }}>
      00:00
    </span>
    <div
      className="scrubber-track"
      onClick={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        setScrub(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)));
      }}
    >
      <div className="scrubber-fill" style={{ width: `${scrub * 100}%` }} />
      <div className="scrubber-handle" style={{ left: `${scrub * 100}%` }} />
    </div>
    <span className="mono" style={{ fontSize: 10, color: 'var(--color-ink-tertiary)' }}>
      {durationLabel}
    </span>
  </div>
);
