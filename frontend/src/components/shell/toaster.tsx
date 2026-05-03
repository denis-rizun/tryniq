'use client';

import { Toaster as SonnerToaster } from 'sonner';

export const Toaster = () => (
  <SonnerToaster
    position="bottom-right"
    offset={20}
    gap={10}
    duration={4500}
    visibleToasts={4}
    toastOptions={{
      unstyled: true,
      classNames: {
        toast: 'tryniq-toast',
        title: 'tryniq-toast__title',
        description: 'tryniq-toast__desc',
        icon: 'tryniq-toast__icon',
      },
    }}
  />
);
