type Kind = 'idle' | 'live' | 'final';

const classFor: Record<Kind, string> = {
  idle: 'status-dot',
  live: 'status-dot status-dot-live rec-dot',
  final: 'status-dot status-dot-final',
};

export const StatusDot = ({ kind = 'idle' }: { kind?: Kind }) => (
  <span className={classFor[kind]} />
);

export const RecIndicator = ({ time }: { time: string }) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
    <span
      className="rec-dot"
      style={{
        width: 8,
        height: 8,
        background: 'var(--color-accent-500)',
        borderRadius: '50%',
        display: 'inline-block',
      }}
    />
    <span className="mono" style={{ fontSize: 12, color: 'var(--color-ink)' }}>
      {time}
    </span>
  </span>
);
