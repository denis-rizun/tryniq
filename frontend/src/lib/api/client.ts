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

export const apiDelete = async (path: string): Promise<void> => {
  const res = await fetch(`${config.apiBaseUrl}${path}`, {
    method: 'DELETE',
    cache: 'no-store',
  });
  if (!res.ok && res.status !== 204) {
    throw new ApiError(res.status, `DELETE ${path} failed: ${res.status}`);
  }
};
