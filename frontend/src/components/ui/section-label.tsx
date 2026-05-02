import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface SectionLabelProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  collapsible?: boolean;
  collapsed?: boolean;
  right?: ReactNode;
}

export const SectionLabel = ({
  children,
  className,
  onClick,
  collapsible,
  collapsed,
  right,
}: SectionLabelProps) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: 12,
    }}
  >
    <span
      className={cn('section-label', className, collapsible && 'collapsible')}
      onClick={onClick}
      style={{ marginBottom: 0 }}
    >
      {collapsible && <span className="toggle">{collapsed ? '▸' : '▾'}</span>}
      {children}
    </span>
    {right}
  </div>
);
