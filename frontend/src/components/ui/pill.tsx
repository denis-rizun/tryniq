import type { ReactNode } from 'react';

export const Pill = ({ children }: { children: ReactNode }) => (
  <span className="pill">{children}</span>
);
