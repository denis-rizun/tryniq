import { useMemo } from 'react';
import { Avatar } from '@/components/ui/avatar';
import type { Person, Utterance as UtteranceType } from '@/lib/types';
import { cn } from '@/lib/utils';
import { splitWords } from './split-words';

interface UtteranceProps {
  u: UtteranceType;
  person: Person;
  isActive: boolean;
  isLive: boolean;
  animate: boolean;
  flashId: string | null;
  outlinedId: string | null;
  showLowConf: boolean;
  onClick?: (u: UtteranceType) => void;
}

export const Utterance = ({
  u,
  person,
  isActive,
  isLive,
  animate,
  flashId,
  outlinedId,
  showLowConf,
  onClick,
}: UtteranceProps) => {
  const words = useMemo(() => splitWords(u.text, u.lowWords), [u.text, u.lowWords]);

  return (
    <div
      className={cn(
        'utterance',
        isActive && 'active-speaker',
        flashId === u.id && 'flash',
        outlinedId === u.id && 'outlined',
      )}
      data-utt-id={u.id}
      onClick={() => onClick?.(u)}
    >
      <Avatar person={person} />
      <div>
        <div className="utterance-meta">
          <span className="utterance-name">{person.name}</span>
          <span className="utterance-time">{u.time}</span>
          {isActive && <span className="utterance-speaking">speaking</span>}
        </div>
        <div className={cn('utterance-body', isLive && 'live')}>
          {words.map((w) => {
            if (w.kind === 'space') return <span key={w.key}>{w.text}</span>;
            return (
              <span
                key={w.key}
                className={cn(animate && 'word-in', w.low && showLowConf && 'word-low')}
                style={animate ? { animationDelay: `${w.idx * 80}ms` } : undefined}
                title={w.low ? 'confidence 0.45' : undefined}
              >
                {w.text}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
};
