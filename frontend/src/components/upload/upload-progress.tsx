import { STAGES } from './upload-stages';

interface ProgressProps {
  stage: number;
  onCancel: () => void;
}

export const UploadProgress = ({ stage, onCancel }: ProgressProps) => (
  <div
    style={{
      background: 'var(--color-paper-lift)',
      border: '1px solid var(--color-border)',
      borderRadius: 4,
      padding: 24,
    }}
  >
    <div
      className="mono"
      style={{ fontSize: 12, color: 'var(--color-ink-secondary)', marginBottom: 14 }}
    >
      standup-2026-05-11.m4a · 24.8 MB
    </div>
    {STAGES.map((s, i) => {
      const done = stage > i;
      const active = stage === i;
      return (
        <div
          key={s.label}
          style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}
        >
          <span
            className="status-dot"
            style={{
              background: done
                ? 'var(--color-decision)'
                : active
                  ? 'var(--color-accent-500)'
                  : 'var(--color-ink-tertiary)',
              animation: active ? 'pulse-rec 1.6s ease-in-out infinite' : 'none',
            }}
          />
          <span
            style={{
              flex: 1,
              fontSize: 13,
              color: done || active ? 'var(--color-ink)' : 'var(--color-ink-tertiary)',
            }}
          >
            {s.label}
          </span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--color-ink-secondary)' }}>
            {active ? s.detail : done ? '✓' : ''}
          </span>
        </div>
      );
    })}
    <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
      <button type="button" className="btn btn-sm" onClick={onCancel}>
        Cancel
      </button>
    </div>
  </div>
);
