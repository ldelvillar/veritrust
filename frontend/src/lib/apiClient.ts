import { CONFIG } from '@/config';

export type GetTokenFn = (options?: {
  template?: string;
}) => Promise<string | null>;

const TOKEN_TEMPLATE = 'veritrust-api';
const AUTH_TOKEN_ERROR = 'No se pudo obtener el token de autenticación.';

interface AuthRequestOptions extends Omit<RequestInit, 'headers' | 'body'> {
  tokenTemplate?: string;
  headers?: HeadersInit;
  body?: unknown;
  errorContextMessage?: string;
}

function buildApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${CONFIG.API_URL}${normalizedPath}`;
}

function getErrorDetailMessage(detail: unknown): string | null {
  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (
      typeof first === 'object' &&
      first !== null &&
      'msg' in first &&
      typeof first.msg === 'string'
    ) {
      return first.msg;
    }
  }

  return null;
}

export async function fetchJsonWithAuth<TResponse>(
  getToken: GetTokenFn,
  path: string,
  options: AuthRequestOptions = {}
): Promise<TResponse> {
  const {
    tokenTemplate = TOKEN_TEMPLATE,
    headers: customHeaders,
    body,
    errorContextMessage = 'Error al conectar con el servidor',
    ...requestInit
  } = options;

  const token = await getToken({ template: tokenTemplate });
  if (!token) {
    throw new Error(AUTH_TOKEN_ERROR);
  }

  const headers = new Headers(customHeaders);
  headers.set('Authorization', `Bearer ${token}`);

  let requestBody: BodyInit | undefined;
  if (body !== undefined) {
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    requestBody = JSON.stringify(body);
  }

  const response = await fetch(buildApiUrl(path), {
    ...requestInit,
    headers,
    body: requestBody,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detailMessage = getErrorDetailMessage(
      (payload as { detail?: unknown }).detail
    );
    throw new Error(
      detailMessage ?? `Status ${response.status}: ${errorContextMessage}`
    );
  }

  return (await response.json()) as TResponse;
}
