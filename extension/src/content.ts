import { MESSAGE_SOURCE, STATE_PUSH_INTERVAL_MS } from "./constants";
import { DomObserver } from "./dom-observer";
import { createMeeting, finalizeMeeting } from "./meeting-api";
import { broadcastState, buildContentState, type RecordingIntent } from "./state-publisher";
import { createStreamSlot, handleVoiceActivityEvent } from "./stream-manager";
import { detectTabKind, isInjectableTab } from "./tab-detection";
import { loadSettings, persistSettings } from "./settings";
import { isPlaceholderName } from "./speaker-naming";
import type { ExtensionSettings, RuntimeMessage, StreamSlot } from "./types";

const tabKind = detectTabKind();
const streams = new Map<string, StreamSlot>();

let settings: ExtensionSettings = {
  gatewayWebSocketUrl: "ws://localhost:8000/api/v1",
  gatewayHttpUrl: "http://localhost:8000/api/v1",
  captureMicrophone: true,
};
let recording = false;
let recordingIntent: RecordingIntent = null;
let meetingId: string | null = null;
let startedAt: number | null = null;
let stateIntervalId: number | null = null;

const pushState = (): void => {
  const ok = broadcastState(
    buildContentState({ recording, recordingIntent, meetingId, startedAt, streams, tabKind }),
  );
  if (!ok && stateIntervalId !== null) {
    clearInterval(stateIntervalId);
    stateIntervalId = null;
  }
};

const domObserver = new DomObserver((event) => {
  if (event.kind === "active") {
    for (const slot of streams.values()) {
      if (slot.participantId !== event.participantId) continue;
      slot.active = event.active;
      slot.webSocket?.sendControl({ type: "speaker_active", active: event.active, t: event.t });
    }
    pushState();
    return;
  }
  for (const slot of streams.values()) {
    const matchesSsrc = slot.ssrc === event.ssrc;
    const canRename = isPlaceholderName(slot.displayName) && !isPlaceholderName(event.info.displayName);
    if (!matchesSsrc || !canRename) continue;
    slot.displayName = event.info.displayName;
    slot.participantId = event.info.participantId;
    slot.webSocket?.sendControl({ type: "speaker_renamed", new_name: event.info.displayName });
  }
  pushState();
});

const injectMainWorld = (): void => {
  if (!isInjectableTab(tabKind)) return;
  window.postMessage(
    { source: MESSAGE_SOURCE, kind: "_worklet_url", url: chrome.runtime.getURL("audio-worklet.js") },
    "*",
  );
};

const startRecording = async (): Promise<void> => {
  if (recording) return;
  settings = await loadSettings();
  try {
    meetingId = await createMeeting(settings.gatewayHttpUrl, {
      title: document.body.dataset.meetingTitle || document.title,
      meet_url: location.href,
    });
    startedAt = Date.now();
  } catch (error) {
    console.error("[tryniq] failed to create meeting", error);
    recordingIntent = null;
    pushState();
    return;
  }
  domObserver.start();
  recording = true;
  recordingIntent = null;
  window.postMessage({ source: MESSAGE_SOURCE, kind: "start" }, "*");
  pushState();
};

const stopRecording = async (): Promise<void> => {
  if (!recording) return;
  recording = false;
  window.postMessage({ source: MESSAGE_SOURCE, kind: "stop" }, "*");
  for (const slot of streams.values()) slot.webSocket?.close();
  streams.clear();
  domObserver.stop();
  if (meetingId) {
    try { await finalizeMeeting(settings.gatewayHttpUrl, meetingId); }
    catch (error) { console.warn("[tryniq] failed to end meeting", error); }
  }
  meetingId = null;
  startedAt = null;
  recordingIntent = null;
  pushState();
};

const attachStream = async (args: { streamId: string; ssrc: number | null; isLocal: boolean }): Promise<void> => {
  if (!meetingId) return;
  if (args.isLocal && !settings.captureMicrophone) return;
  const slot = await createStreamSlot({
    streamId: args.streamId,
    ssrc: args.ssrc,
    isLocal: args.isLocal,
    meetingId,
    settings,
    domObserver,
    onSlotConnected: pushState,
  });
  streams.set(args.streamId, slot);
  pushState();
};

const handleSsrcUpdate = async (streamId: string, ssrc: number): Promise<void> => {
  const slot = streams.get(streamId);
  if (!slot || slot.ssrc !== null) return;
  slot.ssrc = ssrc;
  const info = await domObserver.lookupBySsrc(ssrc);
  const previousName = slot.displayName;
  slot.displayName = info.displayName;
  slot.participantId = info.participantId;
  if (isPlaceholderName(previousName) && !isPlaceholderName(info.displayName)) {
    slot.webSocket?.sendControl({ type: "speaker_renamed", new_name: info.displayName });
  }
  pushState();
};

const handlePcmFrame = async (streamId: string, pcm: ArrayBuffer, timestamp: number): Promise<void> => {
  const slot = streams.get(streamId);
  if (!slot || slot.muted) return;
  const events = await slot.voiceActivityDetector.push(new Int16Array(pcm), timestamp);
  for (const event of events) handleVoiceActivityEvent(slot, event, domObserver, pushState);
};

const removeStream = (streamId: string, sendDiscardReason?: string): void => {
  const slot = streams.get(streamId);
  if (!slot) return;
  if (sendDiscardReason) slot.webSocket?.sendControl({ type: "discard", reason: sendDiscardReason });
  slot.webSocket?.close();
  streams.delete(streamId);
  pushState();
};

window.addEventListener("message", async (event: MessageEvent) => {
  if (event.source !== window) return;
  const data = event.data;
  if (!data || data.source !== MESSAGE_SOURCE) return;

  if (data.kind === "track") await attachStream({ streamId: data.streamId, ssrc: data.ssrc, isLocal: data.isLocal });
  else if (data.kind === "track_ssrc") await handleSsrcUpdate(data.streamId, data.ssrc);
  else if (data.kind === "pcm") await handlePcmFrame(data.streamId, data.pcm, data.t);
  else if (data.kind === "ghost_track") removeStream(data.streamId, data.reason);
  else if (data.kind === "track_ended") removeStream(data.streamId);
  else if (data.kind === "tap_installed" && data.peerConnectionCount === 0 && recording) {
    console.warn("[tryniq] No audio tracks detected after 10s — possible Worker-scope WebRTC (R1).");
  }
});

chrome.runtime.onMessage.addListener((message: RuntimeMessage, _sender, sendResponse) => {
  if (message.kind === "popup.get_state") {
    sendResponse({
      state: buildContentState({ recording, recordingIntent, meetingId, startedAt, streams, tabKind }),
    });
    return true;
  }
  if (message.kind === "popup.start") {
    if (!recording && recordingIntent !== "starting") {
      recordingIntent = "starting";
      pushState();
    }
    void startRecording();
    sendResponse({ ok: true });
    return true;
  }
  if (message.kind === "popup.stop") {
    if (recording && recordingIntent !== "stopping") {
      recordingIntent = "stopping";
      pushState();
    }
    void stopRecording();
    sendResponse({ ok: true });
    return true;
  }
  if (message.kind === "popup.set_settings") {
    void persistSettings(settings, { gatewayUrl: message.gatewayUrl, captureMicrophone: message.captureMicrophone })
      .then((updated) => { settings = updated; });
    sendResponse({ ok: true });
    return true;
  }
  if (message.kind === "popup.mute_stream") {
    const slot = streams.get(message.streamId);
    if (slot) { slot.muted = message.muted; pushState(); }
    sendResponse({ ok: true });
    return true;
  }
  return false;
});

(async () => {
  settings = await loadSettings();
  injectMainWorld();
  stateIntervalId = setInterval(pushState, STATE_PUSH_INTERVAL_MS) as unknown as number;
})();
