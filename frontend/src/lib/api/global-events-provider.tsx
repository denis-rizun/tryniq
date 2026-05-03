'use client';

import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { toast } from 'sonner';
import { subscribeGlobalEvents } from './events';

export const GlobalEventsProvider = () => {
  const queryClient = useQueryClient();

  useEffect(() => {
    const unsubscribe = subscribeGlobalEvents({
      onEvent: (event) => {
        if (event.kind !== 'meeting_lifecycle') return;
        queryClient.invalidateQueries({ queryKey: ['meetings'] });
        if (event.event === 'started') {
          toast('Meeting started', { description: 'Capture in progress.' });
        } else if (event.event === 'ended') {
          toast('Meeting ended', { description: 'Capture stopped.' });
        } else if (event.event === 'final') {
          queryClient.invalidateQueries({ queryKey: ['transcript', event.meeting_id] });
          toast.success('Post-meeting transcription ended', {
            description: 'Refined transcript is ready.',
          });
        }
      },
    });
    return unsubscribe;
  }, [queryClient]);

  return null;
};
