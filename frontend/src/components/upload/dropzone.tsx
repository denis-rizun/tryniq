import { useState } from 'react';
import { Icon } from '@/components/ui/icon';
import { cn } from '@/lib/utils';

interface DropzoneProps {
  onStart: () => void;
}

export const Dropzone = ({ onStart }: DropzoneProps) => {
  const [over, setOver] = useState(false);
  return (
    <div
      className={cn('dropzone', over && 'over')}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        onStart();
      }}
      onClick={onStart}
    >
      <Icon name="upload" size={32} color="var(--color-ink-tertiary)" />
      <div style={{ marginTop: 12, fontSize: 14 }}>Drop a recording here, or click to choose</div>
      <div
        className="mono"
        style={{ marginTop: 8, fontSize: 11, color: 'var(--color-ink-tertiary)' }}
      >
        .mp3 · .wav · .m4a · .mp4 · .webm
      </div>
    </div>
  );
};
