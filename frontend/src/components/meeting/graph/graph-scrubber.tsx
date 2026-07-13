'use client';

import { useEffect, useRef } from 'react';
import { Icon } from '@/components/ui/icon';

interface GraphScrubberProps {
  scrub: number;
  setScrub: (n: number) => void;
  durationLabel: string;
  playing: boolean;
  setPlaying: (b: boolean) => void;
}

const PLAY_SECONDS = 8;

export const GraphScrubber = ({
  scrub,
  setScrub,
  durationLabel,
  playing,
  setPlaying,
}: GraphScrubberProps) => {
  const rafRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);
  const scrubRef = useRef(scrub);
  scrubRef.current = scrub;

  useEffect(() => {
    if (!playing) {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      lastTsRef.current = null;
      return;
    }
    const step = (ts: number) => {
      if (lastTsRef.current === null) lastTsRef.current = ts;
      const dt = (ts - lastTsRef.current) / 1000;
      lastTsRef.current = ts;
      const next = Math.min(1, scrubRef.current + dt / PLAY_SECONDS);
      setScrub(next);
      if (next >= 1) {
        setPlaying(false);
        return;
      }
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [playing, setScrub, setPlaying]);

  const onPlayClick = () => {
    if (scrub >= 1 && !playing) setScrub(0);
    setPlaying(!playing);
  };

  return (
    <div className="scrubber">
      <button
        type="button"
        className="scrubber-play"
        onClick={onPlayClick}
        aria-label={playing ? 'pause' : 'play'}
      >
        <Icon name={playing ? 'pause' : 'play'} size={12} />
      </button>
      <span className="mono" style={{ fontSize: 10, color: 'var(--color-ink-tertiary)' }}>
        00:00
      </span>
      <div
        className="scrubber-track"
        onClick={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          setScrub(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)));
          setPlaying(false);
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
};
