import type { ContentState, ParticipantView, RuntimeMessage, StreamSlot, TabKind } from "./types";

export type RecordingIntent = "starting" | "stopping" | null;

interface BuildStateArgs {
  recording: boolean;
  recordingIntent: RecordingIntent;
  meetingId: string | null;
  startedAt: number | null;
  streams: Map<string, StreamSlot>;
  tabKind: TabKind;
}

const toParticipantView = (slot: StreamSlot): ParticipantView => ({
  streamId: slot.streamId,
  displayName: slot.displayName,
  isLocalUser: slot.isLocal,
  isActive: slot.active,
  muted: slot.muted,
});

const deriveStatus = (recording: boolean, intent: RecordingIntent): ContentState["status"] => {
  if (intent === "stopping") return "stopping";
  if (recording || intent === "starting") return "recording";
  return "idle";
};

export const buildContentState = (args: BuildStateArgs): ContentState => {
  const slots = Array.from(args.streams.values());
  return {
    status: deriveStatus(args.recording, args.recordingIntent),
    meetingId: args.meetingId ?? undefined,
    startedAt: args.startedAt ?? undefined,
    participants: slots.map(toParticipantView),
    gatewayConnected: slots.length > 0 ? slots.some((slot) => slot.initSent) : args.recording,
    tabKind: args.tabKind,
  };
};

let lastSerialized: string | null = null;

export const broadcastState = (state: ContentState): boolean => {
  const serialized = JSON.stringify(state);
  if (serialized === lastSerialized) return true;
  lastSerialized = serialized;
  const message: RuntimeMessage = { kind: "content.state_update", state };
  try {
    chrome.runtime.sendMessage(message).catch(() => {});
    return true;
  } catch {
    return false;
  }
};
