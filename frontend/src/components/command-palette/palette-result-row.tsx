import { Avatar } from '@/components/ui/avatar';
import { StatusDot } from '@/components/ui/status-dot';
import { formatTimestamp } from '@/lib/format';
import { cn } from '@/lib/utils';
import type { PaletteItem } from './types';

interface PaletteResultRowProps {
  active: boolean;
  item: PaletteItem;
  onAction: (item: PaletteItem) => void;
  onHover: () => void;
}

export const PaletteResultRow = ({ active, item, onAction, onHover }: PaletteResultRowProps) => (
  <div
    className={cn('cmd-row', active && 'active')}
    onMouseEnter={onHover}
    onClick={() => onAction(item)}
  >
    {item._kind === 'meeting' && (
      <>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <StatusDot kind={item.state === 'live' ? 'live' : 'final'} />
          {item.title}
        </div>
        <span className="right">{item.relativeStart}</span>
      </>
    )}
    {item._kind === 'person' && (
      <>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Avatar person={item} />
          {item.name}
        </div>
        <span className="right">person</span>
      </>
    )}
    {item._kind === 'utterance' && (
      <>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0, flex: 1 }}>
          <div
            style={{
              fontSize: 13,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {item.text}
          </div>
          <div className="mono" style={{ fontSize: 10, color: 'var(--color-ink-tertiary)' }}>
            {item.participantName ?? 'Speaker'} · {item.meetingTitle}
          </div>
        </div>
        <span className="right mono">{formatTimestamp(item.tStart)}</span>
      </>
    )}
    {item._kind === 'action' && (
      <>
        <div style={{ color: item.isAsk ? 'var(--color-accent-500)' : 'inherit' }}>
          {item.label}
        </div>
        <span className="right">{item.kbd}</span>
      </>
    )}
  </div>
);
