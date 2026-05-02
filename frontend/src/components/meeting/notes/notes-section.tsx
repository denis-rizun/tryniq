'use client';

import { type ReactNode, useState } from 'react';
import { SectionLabel } from '@/components/ui/section-label';

interface NotesSectionProps {
  label: string;
  count?: number;
  defaultCollapsed?: boolean;
  children: ReactNode;
}

export const NotesSection = ({ label, count, defaultCollapsed, children }: NotesSectionProps) => {
  const [collapsed, setCollapsed] = useState(!!defaultCollapsed);
  return (
    <div className="notes-section">
      <SectionLabel
        collapsible
        collapsed={collapsed}
        onClick={() => setCollapsed((c) => !c)}
        right={
          count != null ? (
            <span className="mono" style={{ fontSize: 11, color: 'var(--color-ink-tertiary)' }}>
              {count}
            </span>
          ) : null
        }
      >
        {label}
      </SectionLabel>
      {!collapsed && <div>{children}</div>}
    </div>
  );
};
