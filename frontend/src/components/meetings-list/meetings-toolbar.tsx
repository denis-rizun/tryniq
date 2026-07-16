import { Icon } from '@/components/ui/icon';

interface ToolbarProps {
  query: string;
  onChangeQuery: (query: string) => void;
  onUpload: () => void;
}

export const MeetingsToolbar = ({ query, onChangeQuery, onUpload }: ToolbarProps) => (
  <div style={{ display: 'flex', gap: 10, marginBottom: 18, alignItems: 'center' }}>
    <div style={{ position: 'relative', flex: '0 1 320px' }}>
      <input
        className="input"
        style={{ paddingLeft: 30 }}
        placeholder="Search meetings…"
        value={query}
        onChange={(e) => onChangeQuery(e.target.value)}
      />
      <span
        style={{
          position: 'absolute',
          left: 10,
          top: '50%',
          transform: 'translateY(-50%)',
          display: 'inline-flex',
          color: 'var(--color-ink-tertiary)',
          pointerEvents: 'none',
        }}
      >
        <Icon name="search" size={14} />
      </span>
      <span
        style={{
          position: 'absolute',
          right: 8,
          top: '50%',
          transform: 'translateY(-50%)',
          display: 'inline-flex',
        }}
      >
        <span className="kbd mono">⌘K</span>
      </span>
    </div>
    <button type="button" className="btn">
      Filter ▾
    </button>
    <div style={{ flex: 1 }} />
    <button type="button" className="btn" onClick={onUpload}>
      <Icon name="upload" size={13} /> Upload recording
    </button>
  </div>
);
