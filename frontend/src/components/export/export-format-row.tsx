import { SectionLabel } from '@/components/ui/section-label';
import { cn } from '@/lib/utils';
import { EXPORT_FORMATS } from './export-config';

export const ExportFormatRow = ({
  format,
  onChange,
}: {
  format: string;
  onChange: (format: string) => void;
}) => (
  <>
    <SectionLabel>FORMAT</SectionLabel>
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
      {EXPORT_FORMATS.map((item) => (
        <button
          key={item.id}
          type="button"
          className={cn('format-pill', !item.enabled && 'disabled', format === item.id && 'active')}
          onClick={() => item.enabled && onChange(item.id)}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: format === item.id ? 'var(--color-accent-500)' : 'transparent',
              border: format === item.id ? 'none' : '1px solid var(--color-ink-tertiary)',
            }}
          />
          {item.label}
          {!item.enabled && <span style={{ marginLeft: 4 }}>(soon)</span>}
        </button>
      ))}
    </div>
  </>
);
