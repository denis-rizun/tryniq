import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { DEFAULT_GATEWAY_URL } from "../constants";
import type { ContentState, RuntimeMessage } from "../types";

const INITIAL_STATE: ContentState = {
  status: "idle",
  participants: [],
  gatewayConnected: false,
  tabKind: "other",
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

const Popup = () => {
  const [state, setState] = useState<ContentState>(INITIAL_STATE);
  const [gatewayUrl, setGatewayUrl] = useState(DEFAULT_GATEWAY_URL);
  const [captureMicrophone, setCaptureMicrophone] = useState(true);
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
    const intervalId = setInterval(() => forceTimerTick((value) => value + 1), 1000);
    return () => {
      chrome.runtime.onMessage.removeListener(onRuntimeMessage);
      clearInterval(intervalId);
    };
  }, []);

  const isOnSupportedTab = state.tabKind !== "other";
  const isRecording = state.status === "recording";

  const handleStart = async () => {
    await sendRuntimeMessage({ kind: "popup.set_settings", gatewayUrl, captureMicrophone });
    await sendRuntimeMessage({ kind: "popup.start" });
  };
  const handleStop = async () => { await sendRuntimeMessage({ kind: "popup.stop" }); };

  const indicatorClass = !isOnSupportedTab
    ? ""
    : isRecording
      ? state.gatewayConnected ? "green" : "amber"
      : "";
  const statusText = !isOnSupportedTab
    ? "Open a Meet (or fake-Meet) tab"
    : isRecording
      ? `Recording (${formatElapsedTime(state.startedAt)})`
      : "Idle";

  return (
    <div>
      <div className="header">
        <div className={`dot ${indicatorClass}`} />
        <div className="title">Tryniq Capture</div>
      </div>
      <div className="muted">{statusText}</div>

      <div className="row" style={{ marginTop: 10 }}>
        {!isRecording ? (
          <button className="primary" disabled={!isOnSupportedTab} onClick={handleStart}>
            Start recording
          </button>
        ) : (
          <button className="primary stop" onClick={handleStop}>Stop recording</button>
        )}
      </div>

      <div className="row">
        <label>
          <input
            type="checkbox"
            checked={captureMicrophone}
            onChange={(event) => {
              setCaptureMicrophone(event.target.checked);
              sendRuntimeMessage({ kind: "popup.set_settings", captureMicrophone: event.target.checked });
            }}
          />
          {" "}Capture my mic
        </label>
      </div>

      <div className="muted">Participants ({state.participants.length})</div>
      <div className="list">
        {state.participants.length === 0 && <div className="item muted">No active streams yet.</div>}
        {state.participants.map((participant) => (
          <div className="item" key={participant.streamId}>
            <div className="name">{participant.displayName}</div>
            {participant.isLocalUser && <span className="badge you">you</span>}
            {participant.isActive && <span className="badge active">speaking</span>}
            <button
              className="iconbtn"
              title={participant.muted ? "Unmute" : "Mute capture for this stream"}
              onClick={() => sendRuntimeMessage({
                kind: "popup.mute_stream",
                streamId: participant.streamId,
                muted: !participant.muted,
              })}
            >
              {participant.muted ? "🔇" : "🎙"}
            </button>
          </div>
        ))}
      </div>

      <details>
        <summary>Settings</summary>
        <div className="row" style={{ flexDirection: "column", alignItems: "stretch" }}>
          <div className="muted" style={{ marginBottom: 4 }}>Gateway URL</div>
          <input
            type="text"
            value={gatewayUrl}
            onChange={(event) => setGatewayUrl(event.target.value)}
            onBlur={() => sendRuntimeMessage({ kind: "popup.set_settings", gatewayUrl })}
            placeholder={DEFAULT_GATEWAY_URL}
          />
        </div>
      </details>
    </div>
  );
};

const rootElement = document.getElementById("root");
if (rootElement) createRoot(rootElement).render(<Popup />);
