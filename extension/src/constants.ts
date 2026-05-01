export const CLIENT_VERSION = "0.1.0";
export const MESSAGE_SOURCE = "tryniq";
export const WORKLET_PROCESSOR_NAME = "tryniq-capture";

export const DEFAULT_GATEWAY_URL = "ws://localhost:8000/api/v1";

export const TARGET_SAMPLE_RATE = 16000;
export const NATIVE_SAMPLE_RATE = 48000;
export const FRAME_SAMPLES = 3200;

export const VAD_WINDOW_SAMPLES = 512;
export const VAD_ONSET_FRAMES = 1;
export const VAD_HANGOVER_FRAMES = 25;
export const VAD_SPEECH_THRESHOLD = 0.4;
export const VAD_PREROLL_FRAMES = Math.ceil(480 / 32);
export const VAD_STATE_TENSOR_SHAPE = [2, 1, 128] as const;

export const RECONNECT_BACKOFF_MS = [1000, 2000, 5000, 10000, 10000];
export const MAX_BUFFERED_BYTES = 1024 * 1024;
export const BACKPRESSURE_LOG_EVERY = 50;

export const DOM_LOOKUP_TIMEOUT_MS = 2000;
export const DOM_LOOKUP_POLL_MS = 100;

export const STATE_PUSH_INTERVAL_MS = 1000;
export const TAP_TELEMETRY_DELAY_MS = 10_000;

export const SSRC_RESOLVE_ATTEMPTS = 20;
export const SSRC_RESOLVE_INTERVAL_MS = 100;

export const MEET_HOST = "meet.google.com";
export const LOCAL_DEV_HOSTS = ["localhost", "127.0.0.1"];

export const SPEAKER_FALLBACK_PREFIX = "Speaker ";
export const SPEAKER_RESOLVING_LABEL = "Speaker (resolving)";
export const LOCAL_SPEAKER_LABEL = "You";

export const MEET_TILE_SELECTORS = {
  tileRoot: "[data-participant-id].oZRSLe",
  nameContainer: ".ZY8hPc span.notranslate",
  activeSpeakerNode: ".lH9pqf",
  activeSpeakerClass: "kssMZb",
  selfMarker: ".eQJ1qd",
  ssrcAttribute: "data-ssrc",
  participantIdAttribute: "data-participant-id",
} as const;
