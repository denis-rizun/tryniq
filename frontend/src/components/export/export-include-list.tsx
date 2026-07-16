import { Checkbox } from '@/components/ui/checkbox';
import { SectionLabel } from '@/components/ui/section-label';
import type { BlockState } from './build-preview';
import { EXPORT_BLOCKS } from './export-config';

export const ExportIncludeList = ({
  blocks,
  allOn,
  onToggle,
  onToggleAll,
}: {
  blocks: BlockState;
  allOn: boolean;
  onToggle: (id: string) => void;
  onToggleAll: () => void;
}) => (
  <>
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8,
      }}
    >
      <SectionLabel>INCLUDE</SectionLabel>
      <span
        className="mono"
        style={{ fontSize: 11, color: 'var(--color-accent-500)', cursor: 'pointer' }}
        onClick={onToggleAll}
      >
        {allOn ? 'Select none' : 'Select all'}
      </span>
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 18 }}>
      {EXPORT_BLOCKS.map((block) => (
        <label
          key={block.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            cursor: 'pointer',
            padding: '4px 0',
          }}
        >
          <Checkbox checked={blocks[block.id]} onChange={() => onToggle(block.id)} />
          <span style={{ fontSize: 13, flex: 1 }}>{block.label}</span>
          {block.meta && (
            <span className="mono" style={{ fontSize: 11, color: 'var(--color-ink-tertiary)' }}>
              ({block.meta})
            </span>
          )}
        </label>
      ))}
    </div>
  </>
);
