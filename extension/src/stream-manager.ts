import { CLIENT_VERSION, SPEAKER_RESOLVING_LABEL, LOCAL_SPEAKER_LABEL, DOM_LOOKUP_TIMEOUT_MS } from "./constants";
import type { DomObserver } from "./dom-observer";
import { isPlaceholderName } from "./speaker-naming";
import type { ExtensionSettings, StreamSlot, VoiceActivityEvent, WebSocketInitMessage } from "./types";
import { VoiceActivityDetector } from "./voice-activity-detector";
import { StreamWebSocket } from "./websocket-client";

interface AttachStreamArgs {
  streamId: string;
  ssrc: number | null;
  isLocal: boolean;
  meetingId: string;
  settings: ExtensionSettings;
  domObserver: DomObserver;
  onSlotConnected: () => void;
}

const buildInitMessage = (args: {
  meetingId: string;
  streamId: string;
  participantId: string | null;
  displayName: string;
  isLocal: boolean;
}): WebSocketInitMessage => ({
  kind: "init",
  meeting_id: args.meetingId,
  stream_id: args.streamId,
  speaker: {
    tile_id: args.participantId,
    display_name: args.displayName,
    is_local_user: args.isLocal,
  },
  audio_format: { sample_rate: 16000, encoding: "pcm_s16le", channels: 1 },
  client_started_at: new Date().toISOString(),
  client_version: CLIENT_VERSION,
});

export const createStreamSlot = async (args: AttachStreamArgs): Promise<StreamSlot> => {
  const voiceActivityDetector = new VoiceActivityDetector(chrome.runtime.getURL("vendor/silero_vad.onnx"));
  await voiceActivityDetector.init();

  let displayName = args.isLocal ? LOCAL_SPEAKER_LABEL : SPEAKER_RESOLVING_LABEL;
  let participantId: string | null = null;
  if (args.ssrc !== null && !args.isLocal) {
    const info = await args.domObserver.lookupBySsrc(args.ssrc, DOM_LOOKUP_TIMEOUT_MS);
    displayName = info.displayName;
    participantId = info.participantId;
  }

  const init = buildInitMessage({
    meetingId: args.meetingId,
    streamId: args.streamId,
    participantId,
    displayName,
    isLocal: args.isLocal,
  });

  const webSocket = new StreamWebSocket(args.settings.gatewayWebSocketUrl, init);
  const slot: StreamSlot = {
    streamId: args.streamId,
    isLocal: args.isLocal,
    ssrc: args.ssrc,
    displayName,
    participantId,
    webSocket,
    voiceActivityDetector,
    initSent: false,
    muted: false,
    active: false,
    startedAt: Date.now(),
  };

  webSocket.onConnect = () => {
    slot.initSent = true;
    args.onSlotConnected();
  };
  webSocket.open();
  return slot;
};

export const handleVoiceActivityEvent = (
  slot: StreamSlot,
  event: VoiceActivityEvent,
  domObserver: DomObserver,
  onRename: () => void,
): void => {
  if (event.kind === "speech_start") {
    slot.webSocket?.sendControl({ kind: "vad_speech_start", t: event.t });
    for (const prerollFrame of event.preroll) slot.webSocket?.sendPcmFrame(prerollFrame);
    rebindRemoteSpeakerName(slot, domObserver, onRename);
    return;
  }
  if (event.kind === "speech") {
    slot.webSocket?.sendPcmFrame(event.pcm);
    return;
  }
  slot.webSocket?.sendControl({ kind: "vad_speech_end", t: event.t });
};

const rebindRemoteSpeakerName = (slot: StreamSlot, domObserver: DomObserver, onRename: () => void): void => {
  if (slot.isLocal || !isPlaceholderName(slot.displayName)) return;
  const tile = domObserver.guessRemoteSpeakerTile();
  if (!tile) return;
  const info = domObserver.buildInfoForTile(tile);
  if (!info.displayName || isPlaceholderName(info.displayName)) return;
  slot.displayName = info.displayName;
  slot.participantId = info.participantId;
  slot.webSocket?.sendControl({ kind: "speaker_renamed", new_name: info.displayName });
  onRename();
};
