import { config } from '@/lib/config';
import type { GlobalEvent, LiveEvent } from './types';

export interface SubscribeOptions {
  onEvent: (event: LiveEvent) => void;
  onOpen?: () => void;
  onError?: (err: Event) => void;
}

const MEETING_EVENT_KINDS = [
  'meeting_lifecycle',
  'partial_transcript',
  'transcript_segment',
  'graph_patch',
] as const;

export const subscribeMeetingEvents = (
  meetingId: string,
  { onEvent, onOpen, onError }: SubscribeOptions,
): (() => void) => {
  const url = `${config.apiBaseUrl}/meetings/${meetingId}/events`;
  const source = new EventSource(url);

  source.onopen = () => onOpen?.();
  source.onerror = (e) => onError?.(e);

  const handle = (msg: MessageEvent) => {
    if (!msg.data) return;
    try {
      onEvent(JSON.parse(msg.data) as LiveEvent);
    } catch {}
  };
  MEETING_EVENT_KINDS.forEach((kind) => {
    source.addEventListener(kind, handle);
  });

  return () => source.close();
};

export interface GlobalSubscribeOptions {
  onEvent: (event: GlobalEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (err: Event) => void;
}

const toWsUrl = (httpUrl: string) => httpUrl.replace(/^http/, 'ws');

export const subscribeGlobalEvents = ({
  onEvent,
  onOpen,
  onClose,
  onError,
}: GlobalSubscribeOptions): (() => void) => {
  let socket: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;
  let attempt = 0;

  const connect = () => {
    if (closed) return;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    socket = new WebSocket(`${toWsUrl(config.apiBaseUrl)}/events/ws`);
    socket.onopen = () => {
      attempt = 0;
      onOpen?.();
    };
    socket.onerror = (e) => onError?.(e);
    socket.onclose = () => {
      onClose?.();
      if (closed) return;
      const delay = Math.min(15000, 500 * 2 ** attempt);
      attempt += 1;
      reconnectTimer = setTimeout(connect, delay);
    };
    socket.onmessage = (msg) => {
      if (!msg.data) return;
      try {
        const parsed = JSON.parse(msg.data) as GlobalEvent;
        onEvent(parsed);
      } catch {}
    };
  };

  connect();

  return () => {
    closed = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    socket?.close();
  };
};
