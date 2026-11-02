import 'server-only';

import { auth } from '@clerk/nextjs/server';
import { cache } from 'react';

import { serverEnv } from '@/env/server';
import { throwIfNotOk } from '@/lib/apiClient';
import { PLAN_PATH, type PlanResponse } from '@/lib/plan';

const TOKEN_TEMPLATE = 'veritrust-api';

function buildServerUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${serverEnv.apiUrl}${normalized}`;
}

// One token per request, since each Clerk getToken is an API call and the layout and page share it.
const getServerToken = cache(async () => {
  const { getToken } = await auth();
  return getToken({ template: TOKEN_TEMPLATE });
});

export async function fetchJsonServer<T>(path: string): Promise<T> {
  const token = await getServerToken();
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

// One request per render, so the /app layout and the page that reads it share the Plan.
export const fetchPlanServer = cache(() =>
  fetchJsonServer<PlanResponse>(PLAN_PATH)
);
