import 'server-only';

import { auth } from '@clerk/nextjs/server';

import { ApiError, parseErrorDetail } from '@/lib/apiClient';

const TOKEN_TEMPLATE = 'veritrust-api';

function getServerApiBaseUrl(): string {
  return (
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000'
  );
}

function buildServerUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${getServerApiBaseUrl()}${normalized}`;
}

export async function fetchJsonServer<T>(path: string): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken({ template: TOKEN_TEMPLATE });
  if (!token) {
    throw new Error('No se pudo obtener el token de autenticación.');
  }

  const response = await fetch(buildServerUrl(path), {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const { message, code } = parseErrorDetail(
      (payload as { detail?: unknown }).detail
    );
    throw new ApiError(
      message ?? `Status ${response.status}: error al conectar con el servidor`,
      code,
      response.status
    );
  }

  return (await response.json()) as T;
}
