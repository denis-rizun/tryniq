import { useRef, useState } from 'react';
import { Icon } from '@/components/ui/icon';
import { cn } from '@/lib/utils';

interface DropzoneProps {
  onFile: (file: File) => void;
}

const ACCEPT = '.mp3,.wav,.m4a,.mp4,.webm,.ogg,.flac,audio/*,video/mp4,video/webm';

export const Dropzone = ({ onFile }: DropzoneProps) => {
  const [over, setOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onFile(file);
  };

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
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        style={{ display: 'none' }}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <Icon name="upload" size={32} color="var(--color-ink-tertiary)" />
      <div style={{ marginTop: 12, fontSize: 14 }}>Drop a recording here, or click to choose</div>
      <div
        className="mono"
        style={{ marginTop: 8, fontSize: 11, color: 'var(--color-ink-tertiary)' }}
      >
        .mp3 · .wav · .m4a · .mp4 · .webm · .ogg · .flac
      </div>
    </div>
  );
};
