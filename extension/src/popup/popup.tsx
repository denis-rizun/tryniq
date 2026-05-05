import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { DEFAULT_GATEWAY_URL } from "../constants";
import type { ContentState, ParticipantView, RuntimeMessage } from "../types";
import { Check, ChevronDown, ChevronRight, Mic, MicOff } from "./icons";

const INITIAL_STATE: ContentState = {
  status: "idle",
  participants: [],
  gatewayConnected: false,
  tabKind: "other",
};

const AVATAR_PALETTE = [
  "#c8553d", "#5a7a3f", "#b8851f", "#7a4f8a", "#3d6f8a",
  "#a6402b", "#487a6e", "#8a5a3d", "#6b4f7a", "#3d7a55",
];

const colorFromName = (name: string): string => {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0;
  return AVATAR_PALETTE[Math.abs(hash) % AVATAR_PALETTE.length] ?? "#1a1815";
};

const initialsOf = (name: string): string => {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0];
  if (!first) return "?";
  if (parts.length === 1) return first.slice(0, 2).toUpperCase();
  const last = parts[parts.length - 1] ?? first;
  return ((first[0] ?? "") + (last[0] ?? "")).toUpperCase();
};

const formatElapsedTime = (startTimestamp: number | undefined): string => {
  if (!startTimestamp) return "00:00";
  const totalSeconds = Math.floor((Date.now() - startTimestamp) / 1000);
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
};

const sendRuntimeMessage = async <T = unknown>(message: RuntimeMessage): Promise<T | undefined> => {
  try { return await chrome.runtime.sendMessage(message); }
  catch { return undefined; }
};

const Avatar = ({ participant }: { participant: ParticipantView }) => (
  <span
    className="avatar"
    style={{ background: colorFromName(participant.displayName) }}
    aria-hidden
  >
    {initialsOf(participant.displayName)}
  </span>
);

const Popup = () => {
  const [state, setState] = useState<ContentState>(INITIAL_STATE);
  const [gatewayUrl, setGatewayUrl] = useState(DEFAULT_GATEWAY_URL);
  const [captureMicrophone, setCaptureMicrophone] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [, forceTimerTick] = useState(0);

  useEffect(() => {
    chrome.storage.local.get(["gatewayUrl", "captureMic"]).then((stored) => {
      if (typeof stored.gatewayUrl === "string" && stored.gatewayUrl) setGatewayUrl(stored.gatewayUrl);
      if (typeof stored.captureMic === "boolean") setCaptureMicrophone(stored.captureMic);
    });
    const onRuntimeMessage = (message: RuntimeMessage) => {
      if (message.kind === "content.state_update") setState(message.state);
    };
    chrome.runtime.onMessage.addListener(onRuntimeMessage);
    sendRuntimeMessage<{ state: ContentState }>({ kind: "popup.get_state" }).then((response) => {
      if (response?.state) setState(response.state);
    });
    const intervalId = setInterval(() => forceTimerTick((v) => v + 1), 1000);
    return () => {
      chrome.runtime.onMessage.removeListener(onRuntimeMessage);
      clearInterval(intervalId);
    };
  }, []);

  const isOnSupportedTab = state.tabKind !== "other";
  const isRecording = state.status === "recording" || state.status === "stopping";
  const isStopping = state.status === "stopping";

  const handleStart = async () => {
    await sendRuntimeMessage({ kind: "popup.set_settings", gatewayUrl, captureMicrophone });
    await sendRuntimeMessage({ kind: "popup.start" });
  };
  const handleStop = async () => { await sendRuntimeMessage({ kind: "popup.stop" }); };

  const dotClass = useMemo(() => {
    if (!isOnSupportedTab) return "";
    if (!isRecording) return "";
    return state.gatewayConnected ? "live" : "amber";
  }, [isOnSupportedTab, isRecording, state.gatewayConnected]);

  const statusCopy = !isOnSupportedTab
    ? "Open a Meet tab to begin."
    : isStopping
      ? "Finalising the session…"
      : isRecording
        ? state.gatewayConnected ? "Connected to gateway. Capturing audio." : "Reconnecting to gateway…"
        : "Idle. Press start when your meeting begins.";

  return (
    <>
      <div className="topbar">
        <span className={`dot ${dotClass}`} aria-hidden />
        <div className="brand">tryniq</div>
        {isRecording && <div className="timer">{formatElapsedTime(state.startedAt)}</div>}
      </div>

      <div className="section">
        <div className="section-label">Status</div>
        <div className="helper" style={{ marginBottom: 10 }}>{statusCopy}</div>
        {!isRecording ? (
          <button className="btn btn-primary" disabled={!isOnSupportedTab} onClick={handleStart}>
            Start recording
          </button>
        ) : (
          <button className="btn btn-danger" disabled={isStopping} onClick={handleStop}>
            {isStopping ? "Stopping…" : (<><span className="rec-dot" aria-hidden /> Stop recording</>)}
          </button>
        )}
      </div>

      <label className="check-row">
        <input
          type="checkbox"
          checked={captureMicrophone}
          onChange={(event) => {
            setCaptureMicrophone(event.target.checked);
            sendRuntimeMessage({ kind: "popup.set_settings", captureMicrophone: event.target.checked });
          }}
        />
        <span className="check-box"><Check /></span>
        <span className="check-text">
          Capture my microphone
          <span className="helper">Stream your own voice alongside remote participants.</span>
        </span>
      </label>

      <div className="section">
        <div className="section-label">
          Participants
          <span className="count">({state.participants.length})</span>
        </div>
        <div className="list">
          {state.participants.length === 0 && (
            <div className="empty">No active streams yet.</div>
          )}
          {state.participants.map((participant) => (
            <div className="row" key={participant.streamId}>
              <Avatar participant={participant} />
              <div className="name">{participant.displayName}</div>
              {participant.isLocalUser && <span className="pill you">you</span>}
              {participant.isActive && <span className="pill speaking">speaking</span>}
              <button
                className={`icon-btn${participant.muted ? " muted" : ""}`}
                title={participant.muted ? "Unmute capture for this stream" : "Mute capture for this stream"}
                onClick={() => sendRuntimeMessage({
                  kind: "popup.mute_stream",
                  streamId: participant.streamId,
                  muted: !participant.muted,
                })}
              >
                {participant.muted ? <MicOff /> : <Mic />}
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="section">
        <div
          className="section-label collapsible"
          onClick={() => setSettingsOpen((open) => !open)}
          role="button"
          tabIndex={0}
        >
          <span className="toggle">{settingsOpen ? <ChevronDown /> : <ChevronRight />}</span>
          Settings
        </div>
        {settingsOpen && (
          <div>
            <div className="field-label">Gateway URL</div>
            <input
              className="input"
              type="text"
              value={gatewayUrl}
              onChange={(event) => setGatewayUrl(event.target.value)}
              onBlur={() => sendRuntimeMessage({ kind: "popup.set_settings", gatewayUrl })}
              placeholder={DEFAULT_GATEWAY_URL}
            />
          </div>
        )}
      </div>
    </>
  );
};

const rootElement = document.getElementById("root");
if (rootElement) createRoot(rootElement).render(<Popup />);
