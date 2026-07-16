import { BACKPRESSURE_LOG_EVERY, MAX_BUFFERED_BYTES, RECONNECT_BACKOFF_MS } from "./constants";
import type { WebSocketControlMessage, WebSocketInitMessage } from "./types";

const buildStreamUrl = (gatewayBaseUrl: string, init: WebSocketInitMessage): string => {
  const trimmedBase = gatewayBaseUrl.replace(/\/$/, "");
  return `${trimmedBase}/meetings/${init.meeting_id}/streams/${init.stream_id}`;
};

export class StreamWebSocket {
  private socket: WebSocket | null = null;
  private readonly url: string;
  private reconnectAttempt = 0;
  private droppedFrameCount = 0;
  private closedByUser = false;
  private awaitingInit = true;

  onConnect?: () => void;
  onClose?: () => void;
  onError?: (error: Event | Error) => void;

  constructor(gatewayBaseUrl: string, private readonly init: WebSocketInitMessage) {
    this.url = buildStreamUrl(gatewayBaseUrl, init);
  }

  open = (): void => {
    this.closedByUser = false;
    this.connect();
  };

  close = (): void => {
    this.closedByUser = true;
    const socket = this.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    try { socket.send(JSON.stringify({ kind: "stream_end" })); } catch {}
    try { socket.close(1000, "client stop"); } catch {}
  };

  sendPcmFrame = (pcm: Int16Array): void => {
    const socket = this.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN || this.awaitingInit) return;
    if (socket.bufferedAmount > MAX_BUFFERED_BYTES) {
      this.droppedFrameCount += 1;
      if (this.droppedFrameCount % BACKPRESSURE_LOG_EVERY === 0) {
        console.warn(`[tryniq] backpressure drop x${this.droppedFrameCount}`);
      }
      return;
    }
    socket.send(pcm.buffer);
  };

  sendControl = (message: WebSocketControlMessage): void => {
    const socket = this.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify(message));
  };

  private connect = (): void => {
    try {
      this.socket = new WebSocket(this.url);
    } catch (error) {
      this.onError?.(error as Error);
      this.scheduleReconnect();
      return;
    }
    this.socket.binaryType = "arraybuffer";
    this.socket.onopen = this.handleOpen;
    this.socket.onclose = this.handleClose;
    this.socket.onerror = (event) => this.onError?.(event);
  };

  private handleOpen = (): void => {
    this.reconnectAttempt = 0;
    this.socket?.send(JSON.stringify(this.init));
    this.awaitingInit = false;
    this.onConnect?.();
  };

  private handleClose = (): void => {
    this.onClose?.();
    if (!this.closedByUser) this.scheduleReconnect();
  };

  private scheduleReconnect = (): void => {
    if (this.reconnectAttempt >= RECONNECT_BACKOFF_MS.length) return;
    const waitMs = RECONNECT_BACKOFF_MS[this.reconnectAttempt]!;
    this.reconnectAttempt += 1;
    setTimeout(() => {
      if (this.closedByUser) return;
      this.awaitingInit = true;
      this.connect();
    }, waitMs);
  };
}
