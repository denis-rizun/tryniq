import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import type { ReactNode } from 'react';
import { ShellOverlays } from '@/components/shell/shell-overlays';
import { Sidebar } from '@/components/shell/sidebar';
import { Toaster } from '@/components/shell/toaster';
import { Topbar } from '@/components/shell/topbar';
import { GlobalEventsProvider } from '@/lib/api/global-events-provider';
import { QueryProvider } from '@/lib/api/query-client';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' });

export const metadata: Metadata = {
  title: 'tryniq',
};

export const viewport: Viewport = {
  width: 1280,
};

const RootLayout = ({ children }: { children: ReactNode }) => (
  <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
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
