import type { VoiceActivityDetector } from "./voice-activity-detector";
import type { StreamWebSocket } from "./websocket-client";

export type TabKind = "meet" | "fake-meet" | "other";

export type RecordingStatus = "idle" | "starting" | "recording" | "reconnecting" | "error";

export interface Speaker {
  tile_id: string | null;
  display_name: string;
  is_local_user: boolean;
}

export interface AudioFormat {
  sample_rate: 16000;
  encoding: "pcm_s16le";
  channels: 1;
}

export interface WebSocketInitMessage {
  type: "init";
  meeting_id: string;
  stream_id: string;
  speaker: Speaker;
  audio_format: AudioFormat;
  client_started_at: string;
  client_version: string;
}

export type WebSocketControlMessage =
  | { type: "vad_speech_start"; t: number }
  | { type: "vad_speech_end"; t: number }
  | { type: "speaker_active"; active: boolean; t: number }
  | { type: "speaker_renamed"; new_name: string }
  | { type: "discard"; reason?: string }
  | { type: "stream_end" };

export type VoiceActivityEvent =
  | { kind: "speech_start"; t: number; preroll: Int16Array[] }
  | { kind: "speech"; t: number; pcm: Int16Array }
  | { kind: "speech_end"; t: number };

export interface ParticipantInfo {
  participantId: string | null;
  displayName: string;
  isLocal: boolean;
  isActive: boolean;
  tileElement: HTMLElement | null;
}

export type DomObserverEvent =
  | { kind: "name"; ssrc: number; info: ParticipantInfo }
  | { kind: "active"; participantId: string; active: boolean; t: number };

export type MainWorldMessage =
  | { source: "tryniq"; kind: "tap_installed"; peerConnectionCount: number }
  | {
      source: "tryniq";
      kind: "track";
      streamId: string;
      trackId: string;
      ssrc: number | null;
      mediaStreamIdentifier: string | null;
      isLocal: boolean;
    }
  | { source: "tryniq"; kind: "track_ssrc"; streamId: string; ssrc: number }
  | { source: "tryniq"; kind: "pcm"; streamId: string; t: number; pcm: ArrayBuffer }
  | { source: "tryniq"; kind: "track_ended"; streamId: string }
  | { source: "tryniq"; kind: "ghost_track"; streamId: string; reason?: string };

export type IsolatedWorldMessage =
  | { source: "tryniq"; kind: "start" }
  | { source: "tryniq"; kind: "stop" }
  | { source: "tryniq"; kind: "stop_stream"; streamId: string }
  | { source: "tryniq"; kind: "_worklet_url"; url: string };

export type RuntimeMessage =
  | { kind: "popup.get_state" }
  | { kind: "popup.start" }
  | { kind: "popup.stop" }
  | { kind: "popup.set_settings"; gatewayUrl?: string; captureMicrophone?: boolean }
  | { kind: "popup.mute_stream"; streamId: string; muted: boolean }
  | { kind: "content.state_update"; state: ContentState };

export interface ParticipantView {
  streamId: string;
  displayName: string;
  isLocalUser: boolean;
  isActive: boolean;
  muted: boolean;
}

export interface ContentState {
  status: RecordingStatus;
  errorMessage?: string;
  meetingId?: string;
  startedAt?: number;
  participants: ParticipantView[];
  gatewayConnected: boolean;
  tabKind: TabKind;
}

export interface StreamSlot {
  streamId: string;
  isLocal: boolean;
  ssrc: number | null;
  displayName: string;
  participantId: string | null;
  webSocket: StreamWebSocket | null;
  voiceActivityDetector: VoiceActivityDetector;
  initSent: boolean;
  muted: boolean;
  active: boolean;
  startedAt: number;
}

export interface ExtensionSettings {
  gatewayWebSocketUrl: string;
  gatewayHttpUrl: string;
  captureMicrophone: boolean;
}
