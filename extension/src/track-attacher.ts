import {
  MESSAGE_SOURCE,
  NATIVE_SAMPLE_RATE,
  SSRC_RESOLVE_ATTEMPTS,
  SSRC_RESOLVE_INTERVAL_MS,
  WORKLET_PROCESSOR_NAME,
} from "./constants";

interface TrackContext {
  streamId: string;
  trackId: string;
  isLocal: boolean;
  audioContext: AudioContext;
  sourceNode: MediaStreamAudioSourceNode | null;
  workletNode: AudioWorkletNode | null;
  ssrc: number | null;
  ended: boolean;
}

interface AttachTrackArgs {
  track: MediaStreamTrack;
  isLocal: boolean;
  transceiver: RTCRtpTransceiver | null;
  workletUrl: string;
  attachedTrackIds: Set<string>;
  trackContexts: Map<string, TrackContext>;
}

const postToIsolated = (message: unknown, transferables: Transferable[] = []): void => {
  window.postMessage(message, "*", transferables);
};

const cleanupTrackContext = (context: TrackContext): void => {
  context.ended = true;
  try { context.workletNode?.disconnect(); } catch {}
  try { context.sourceNode?.disconnect(); } catch {}
  try { context.audioContext.close(); } catch {}
};

let workletModuleLoaded = false;

const ensureWorkletModule = async (audioContext: AudioContext, workletUrl: string): Promise<void> => {
  if (workletModuleLoaded) return;
  await audioContext.audioWorklet.addModule(workletUrl);
  workletModuleLoaded = true;
};

const resolveTransceiverSsrc = async (transceiver: RTCRtpTransceiver): Promise<number | null> => {
  for (let attempt = 0; attempt < SSRC_RESOLVE_ATTEMPTS; attempt++) {
    const receiver = transceiver.receiver;
    const sources = (receiver as { getSynchronizationSources?: () => RTCRtpSynchronizationSource[] })
      .getSynchronizationSources?.();
    const directSsrc = sources?.[0]?.source;
    if (typeof directSsrc === "number" && directSsrc !== 0) return directSsrc;
    try {
      const stats = await receiver.getStats();
      let foundSsrc: number | null = null;
      stats.forEach((report: { type?: string; ssrc?: number }) => {
        if (report.type === "inbound-rtp" && typeof report.ssrc === "number" && report.ssrc !== 0) {
          foundSsrc = report.ssrc;
        }
      });
      if (foundSsrc !== null) return foundSsrc;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, SSRC_RESOLVE_INTERVAL_MS));
  }
  return null;
};

export const attachTrack = async (args: AttachTrackArgs): Promise<void> => {
  const { track, isLocal, transceiver, workletUrl, attachedTrackIds, trackContexts } = args;
  if (track.kind !== "audio" || attachedTrackIds.has(track.id)) return;
  attachedTrackIds.add(track.id);

  const streamId = crypto.randomUUID();
  const audioContext = new AudioContext({ sampleRate: NATIVE_SAMPLE_RATE });
  await ensureWorkletModule(audioContext, workletUrl);
  if (audioContext.state === "suspended") {
    try { await audioContext.resume(); } catch (error) { console.warn("[tryniq] audioContext.resume failed", error); }
  }
  console.log("[tryniq] attachTrack", { streamId, trackId: track.id, ctxState: audioContext.state, isLocal });

  const sourceNode = audioContext.createMediaStreamSource(new MediaStream([track]));
  const workletNode = new AudioWorkletNode(audioContext, WORKLET_PROCESSOR_NAME, {
    numberOfInputs: 1,
    numberOfOutputs: 0,
    channelCount: 1,
  });
  sourceNode.connect(workletNode);
  const keepAliveGain = audioContext.createGain();
  keepAliveGain.gain.value = 0;
  sourceNode.connect(keepAliveGain);
  keepAliveGain.connect(audioContext.destination);

  workletNode.port.onmessage = (event: MessageEvent) => {
    const data = event.data;
    if (!data || data.kind !== "pcm") return;
    const buffer: ArrayBuffer = data.pcm;
    postToIsolated({ source: MESSAGE_SOURCE, kind: "pcm", streamId, t: data.t, pcm: buffer }, [buffer]);
  };

  const context: TrackContext = {
    streamId,
    trackId: track.id,
    isLocal,
    audioContext,
    sourceNode,
    workletNode,
    ssrc: null,
    ended: false,
  };
  trackContexts.set(streamId, context);

  const ssrc = transceiver?.receiver ? await resolveTransceiverSsrc(transceiver) : null;
  context.ssrc = ssrc;

  postToIsolated({
    source: MESSAGE_SOURCE,
    kind: "track",
    streamId,
    trackId: track.id,
    ssrc,
    mediaStreamIdentifier: transceiver?.mid ?? null,
    isLocal,
  });
  if (ssrc !== null) postToIsolated({ source: MESSAGE_SOURCE, kind: "track_ssrc", streamId, ssrc });

  track.addEventListener("ended", () => {
    cleanupTrackContext(context);
    trackContexts.delete(streamId);
    attachedTrackIds.delete(track.id);
    postToIsolated({ source: MESSAGE_SOURCE, kind: "track_ended", streamId });
  });
};

export const cleanupAllTracks = (trackContexts: Map<string, TrackContext>, attachedTrackIds: Set<string>): void => {
  for (const context of trackContexts.values()) cleanupTrackContext(context);
  trackContexts.clear();
  attachedTrackIds.clear();
};

export const cleanupSingleTrack = (
  trackContexts: Map<string, TrackContext>,
  streamId: string,
): void => {
  const context = trackContexts.get(streamId);
  if (!context) return;
  cleanupTrackContext(context);
  trackContexts.delete(streamId);
};

export type { TrackContext };
