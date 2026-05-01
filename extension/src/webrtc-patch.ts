interface PeerConnectionPatchHandlers {
  onPeerConnectionCreated: (peerConnection: RTCPeerConnection) => void;
  onAudioTrack: (track: MediaStreamTrack, transceiver: RTCRtpTransceiver | null) => void;
}

export const patchRtcPeerConnection = (handlers: PeerConnectionPatchHandlers): void => {
  const NativePeerConnection = window.RTCPeerConnection;
  if (!NativePeerConnection) return;

  const proxiedPeerConnection = new Proxy(NativePeerConnection, {
    construct(target, args) {
      const peerConnection: RTCPeerConnection = new (target as typeof NativePeerConnection)(...(args as []));
      handlers.onPeerConnectionCreated(peerConnection);
      peerConnection.addEventListener("track", (event: RTCTrackEvent) => {
        if (event.track.kind !== "audio") return;
        handlers.onAudioTrack(event.track, event.transceiver ?? null);
      });
      return peerConnection;
    },
  });

  try {
    (window as unknown as { RTCPeerConnection: typeof RTCPeerConnection }).RTCPeerConnection = proxiedPeerConnection;
    console.log("[tryniq] RTCPeerConnection patched (Proxy)");
  } catch (error) {
    console.error("[tryniq] failed to install RTCPeerConnection proxy", error);
  }
};

export const collectExistingAudioTracks = (
  peerConnection: RTCPeerConnection,
  onTrack: (track: MediaStreamTrack, transceiver: RTCRtpTransceiver | null, isLocal: boolean) => void,
): void => {
  for (const transceiver of peerConnection.getTransceivers()) {
    const remoteTrack = transceiver.receiver?.track;
    if (remoteTrack && remoteTrack.kind === "audio" && remoteTrack.readyState === "live") {
      onTrack(remoteTrack, transceiver, false);
    }
  }
  for (const sender of peerConnection.getSenders()) {
    const localTrack = sender.track;
    if (!localTrack || localTrack.kind !== "audio" || localTrack.readyState !== "live") continue;
    const transceiver = peerConnection.getTransceivers().find((entry) => entry.sender === sender) ?? null;
    onTrack(localTrack, transceiver, true);
  }
};
