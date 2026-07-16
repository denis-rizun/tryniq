import { config } from '@/lib/config';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export const apiGet = async <T>(path: string): Promise<T> => {
  const res = await fetch(`${config.apiBaseUrl}${path}`, {
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `GET ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
};

export const apiPatch = async <T>(path: string, body: unknown): Promise<T> => {
  const res = await fetch(`${config.apiBaseUrl}${path}`, {
    method: 'PATCH',
    cache: 'no-store',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, `PATCH ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
};

export const apiPost = async <T>(path: string, body: unknown): Promise<T> => {
  const res = await fetch(`${config.apiBaseUrl}${path}`, {
    method: 'POST',
    cache: 'no-store',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, `POST ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
};

export interface ApiStreamOptions<TEvent> {
  onEvent: (event: TEvent) => void;
  signal?: AbortSignal;
}

export const apiStream = async <TEvent>(
  path: string,
  body: unknown,
  { onEvent, signal }: ApiStreamOptions<TEvent>,
): Promise<void> => {
  const res = await fetch(`${config.apiBaseUrl}${path}`, {
    method: 'POST',
    cache: 'no-store',
    headers: { Accept: 'text/event-stream', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new ApiError(res.status, `POST ${path} failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const data = buffer
          .slice(0, boundary)
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trimStart())
          .join('\n');
        buffer = buffer.slice(boundary + 2);
        if (data) {
          try {
            onEvent(JSON.parse(data) as TEvent);
          } catch {}
        }
        boundary = buffer.indexOf('\n\n');
      }
    }
  } finally {
    try {
      await reader.cancel();
    } catch {}
  }
};

export const apiUpload = async <T>(path: string, form: FormData): Promise<T> => {
  const res = await fetch(`${config.apiBaseUrl}${path}`, { method: 'POST', body: form });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new ApiError(res.status, `POST ${path} failed: ${res.status} ${detail}`);
  }
  return (await res.json()) as T;
};

export interface BlobResponse {
  blob: Blob;
  filename: string | null;
}

export const apiGetBlob = async (path: string): Promise<BlobResponse> => {
  const res = await fetch(`${config.apiBaseUrl}${path}`, { cache: 'no-store' });
  if (!res.ok) {
    throw new ApiError(res.status, `GET ${path} failed: ${res.status}`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition');
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return { blob, filename: match?.[1] ?? null };
};

export const apiDelete = async (path: string): Promise<void> => {
  const res = await fetch(`${config.apiBaseUrl}${path}`, {
    method: 'DELETE',
    cache: 'no-store',
  });
  if (!res.ok && res.status !== 204) {
    throw new ApiError(res.status, `DELETE ${path} failed: ${res.status}`);
  }
};
