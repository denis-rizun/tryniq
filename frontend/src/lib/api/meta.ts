import { apiGet } from './client';

export interface ModelInfo {
  provider: string;
  model: string;
}

export interface ModelsResponse {
  chat: ModelInfo;
  graph: ModelInfo;
  metadata: ModelInfo;
  embeddings: ModelInfo;
  asr_live: ModelInfo;
  asr_final: ModelInfo;
}

export const getModels = () => apiGet<ModelsResponse>('/models');
