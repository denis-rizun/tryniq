'use client';

import { Avatar } from '@/components/ui/avatar';
import { Icon } from '@/components/ui/icon';
import { people } from '@/lib/mock';
import { useUIStore } from '@/lib/store';
import { Breadcrumb } from './breadcrumb';

export const Topbar = () => {
  const { setPaletteOpen, toggleDrawer } = useUIStore();
  return (
    <div className="topbar">
      <span className="topbar-brand">tryniq</span>
      <Breadcrumb />
      <div style={{ flex: 1 }} />
      <button
        type="button"
        className="btn btn-ghost btn-sm mono"
        onClick={() => setPaletteOpen(true)}
      >
        <Icon name="search" size={12} /> Search{' '}
        <span className="kbd mono" style={{ marginLeft: 6 }}>
          ⌘K
        </span>
      </button>
      <button
        type="button"
        className="btn btn-ghost btn-sm mono"
        onClick={() => toggleDrawer()}
        title="AI assistant (⌘J)"
      >
        <Icon name="sparkles" size={12} color="var(--color-ink-secondary)" /> Ask AI{' '}
        <span className="kbd mono" style={{ marginLeft: 6 }}>
          ⌘J
        </span>
      </button>
      <Avatar person={people.anna} />
    </div>
  );
};
