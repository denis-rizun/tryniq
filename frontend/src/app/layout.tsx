import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import { GlobalEventsProvider } from '@/lib/api/global-events-provider';
import { QueryProvider } from '@/lib/api/query-client';
import { ShellOverlays } from '@/components/shell/shell-overlays';
import { Sidebar } from '@/components/shell/sidebar';
import { Toaster } from '@/components/shell/toaster';
import { Topbar } from '@/components/shell/topbar';
import './globals.css';

export const metadata: Metadata = {
  title: 'tryniq',
};

export const viewport: Viewport = {
  width: 1280,
};

const RootLayout = ({ children }: { children: ReactNode }) => (
  <html lang="en">
    <head>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link
        href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap"
        rel="stylesheet"
      />
    </head>
    <body>
      <QueryProvider>
        <GlobalEventsProvider />
        <div className="app-shell">
          <Sidebar />
          <main style={{ minWidth: 0, display: 'flex', flexDirection: 'column' }}>
            <Topbar />
            {children}
            <ShellOverlays />
          </main>
        </div>
        <Toaster />
      </QueryProvider>
    </body>
  </html>
);

export default RootLayout;
