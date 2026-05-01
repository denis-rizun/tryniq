import type { ContentState, ParticipantView, RuntimeMessage, StreamSlot, TabKind } from "./types";

interface BuildStateArgs {
  recording: boolean;
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

export const buildContentState = (args: BuildStateArgs): ContentState => {
  const slots = Array.from(args.streams.values());
  return {
    status: args.recording ? "recording" : "idle",
    meetingId: args.meetingId ?? undefined,
    startedAt: args.startedAt ?? undefined,
    participants: slots.map(toParticipantView),
    gatewayConnected: slots.length > 0 ? slots.some((slot) => slot.initSent) : args.recording,
    tabKind: args.tabKind,
  };
};

export const broadcastState = (state: ContentState): boolean => {
  const message: RuntimeMessage = { kind: "content.state_update", state };
  try {
    chrome.runtime.sendMessage(message).catch(() => {});
    return true;
  } catch {
    return false;
  }
};
