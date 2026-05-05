'use client';

import { useQuery } from '@tanstack/react-query';
import { getModels, type ModelsResponse } from '@/lib/api/meta';

const MODELS_KEY = ['models'] as const;

export const useModels = () =>
  useQuery<ModelsResponse>({
    queryKey: MODELS_KEY,
    queryFn: getModels,
    staleTime: 5 * 60 * 1000,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
  });
