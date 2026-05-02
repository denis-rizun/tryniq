import type { Person } from '@/lib/types';

type Size = 'sm' | 'md' | 'lg';

interface AvatarProps {
  person: Person;
  size?: Size;
}

const sizeClass: Record<Size, string> = {
  sm: 'avatar',
  md: 'avatar avatar-md',
  lg: 'avatar avatar-lg',
};

export const Avatar = ({ person, size = 'sm' }: AvatarProps) => (
  <span
    className={sizeClass[size]}
    style={{ background: person.color, color: '#1A1815', borderColor: 'rgba(26,24,21,0.10)' }}
  >
    {person.initials}
  </span>
);

interface AvatarStackProps {
  people: Person[];
  max?: number;
  size?: Size;
}

export const AvatarStack = ({ people, max = 4, size = 'sm' }: AvatarStackProps) => {
  const shown = people.slice(0, max);
  const extra = people.length - max;
  return (
    <span className="avatar-stack">
      {shown.map((p) => (
        <Avatar key={p.id} person={p} size={size} />
      ))}
      {extra > 0 && (
        <span
          className={size === 'md' ? 'avatar avatar-md' : 'avatar'}
          style={{ background: 'var(--color-paper-active)', color: 'var(--color-ink-secondary)' }}
        >
          +{extra}
        </span>
      )}
    </span>
  );
};
