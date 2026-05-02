interface SpeakerWaveformProps {
  pct: number;
  index: number;
}

const BARS = 60;

export const SpeakerWaveform = ({ pct, index }: SpeakerWaveformProps) => (
  <div
    style={{
      padding: '0 24px 16px 80px',
      display: 'flex',
      alignItems: 'flex-end',
      gap: 2,
      height: 60,
    }}
  >
    {Array.from({ length: BARS }).map((_, k) => {
      const seed = (k + index * 7) % 7;
      const isActive = seed < 3 && (pct / 40 > 0.6 || k % 4 === index % 4);
      return (
        <div
          key={k}
          style={{
            flex: 1,
            height: isActive ? `${20 + seed * 5}px` : '4px',
            background: isActive ? 'var(--color-paper-active)' : 'var(--color-border-subtle)',
            borderRadius: 1,
          }}
        />
      );
    })}
  </div>
);
