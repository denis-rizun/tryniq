import { SPEAKER_FALLBACK_PREFIX, SPEAKER_RESOLVING_LABEL } from "./constants";

export const isPlaceholderName = (displayName: string): boolean =>
  displayName.startsWith(SPEAKER_FALLBACK_PREFIX) || displayName === SPEAKER_RESOLVING_LABEL;
