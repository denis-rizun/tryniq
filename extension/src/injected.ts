import { MESSAGE_SOURCE, TAP_TELEMETRY_DELAY_MS } from "./constants";
import { attachTrack, cleanupAllTracks, cleanupSingleTrack, type TrackContext } from "./track-attacher";
import { collectExistingAudioTracks, patchRtcPeerConnection } from "./webrtc-patch";

const trackContexts = new Map<string, TrackContext>();
const knownPeerConnections = new Set<RTCPeerConnection>();
const attachedTrackIds = new Set<string>();

let recording = false;
let workletUrl = "";

const postToIsolated = (message: unknown): void => window.postMessage(message, "*");

const tryAttachTrack = async (
  track: MediaStreamTrack,
  transceiver: RTCRtpTransceiver | null,
  isLocal: boolean,
): Promise<void> => {
  if (!recording || !workletUrl) return;
  try {
    await attachTrack({ track, isLocal, transceiver, workletUrl, attachedTrackIds, trackContexts });
  } catch (error) {
    console.error("[tryniq] attachTrack failed", error);
  }
};

const startRecording = (): void => {
  recording = true;
  for (const peerConnection of knownPeerConnections) {
    collectExistingAudioTracks(peerConnection, (track, transceiver, isLocal) => {
      void tryAttachTrack(track, transceiver, isLocal);
    });
  }
  postToIsolated({ source: MESSAGE_SOURCE, kind: "tap_installed", peerConnectionCount: knownPeerConnections.size });
  setTimeout(() => {
    postToIsolated({ source: MESSAGE_SOURCE, kind: "tap_installed", peerConnectionCount: trackContexts.size });
  }, TAP_TELEMETRY_DELAY_MS);
};

const stopRecording = (): void => {
  recording = false;
  cleanupAllTracks(trackContexts, attachedTrackIds);
};

patchRtcPeerConnection({
  onPeerConnectionCreated: (peerConnection) => {
    knownPeerConnections.add(peerConnection);
    peerConnection.addEventListener("connectionstatechange", () => {
      if (peerConnection.connectionState === "closed") knownPeerConnections.delete(peerConnection);
    });
  },
  onAudioTrack: (track, transceiver) => { void tryAttachTrack(track, transceiver, false); },
});

window.addEventListener("message", (event: MessageEvent) => {
  if (event.source !== window) return;
  const data = event.data;
  if (!data || data.source !== MESSAGE_SOURCE) return;

  if (data.kind === "_worklet_url") workletUrl = data.url;
  else if (data.kind === "start") startRecording();
  else if (data.kind === "stop") stopRecording();
  else if (data.kind === "stop_stream") cleanupSingleTrack(trackContexts, data.streamId);
});

console.log("[tryniq] injected.js ready");
