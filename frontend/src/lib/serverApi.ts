import 'server-only';

import { auth } from '@clerk/nextjs/server';

import { serverEnv } from '@/env/server';
import { throwIfNotOk } from '@/lib/apiClient';

const TOKEN_TEMPLATE = 'veritrust-api';

function buildServerUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${serverEnv.apiUrl}${normalized}`;
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

  await throwIfNotOk(response, 'error al conectar con el servidor');

  return (await response.json()) as T;
}

export async function fetchPublicJsonServer<T>(path: string): Promise<T> {
  const response = await fetch(buildServerUrl(path), { cache: 'no-store' });

  await throwIfNotOk(response, 'error al conectar con el servidor');

  return (await response.json()) as T;
}
