import { clientEnv } from '@/env/client';

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

export class ApiError extends Error {
  readonly code: string | null;
  readonly status: number;

  constructor(message: string, code: string | null, status: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

export function buildApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${clientEnv.apiUrl}${normalizedPath}`;
}

export interface ParsedErrorDetail {
  message: string | null;
  code: string | null;
}

export function parseErrorDetail(detail: unknown): ParsedErrorDetail {
  if (typeof detail === 'string') {
    return { message: detail, code: null };
  }

  if (typeof detail === 'object' && detail !== null && !Array.isArray(detail)) {
    const obj = detail as Record<string, unknown>;
    const code = typeof obj.code === 'string' ? obj.code : null;
    const message = typeof obj.message === 'string' ? obj.message : null;
    if (code !== null || message !== null) {
      return { message, code };
    }
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (
      typeof first === 'object' &&
      first !== null &&
      'msg' in first &&
      typeof first.msg === 'string'
    ) {
      return { message: first.msg, code: null };
    }
  }

  return { message: null, code: null };
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
    const { message, code } = parseErrorDetail(
      (payload as { detail?: unknown }).detail
    );
    throw new ApiError(
      message ?? `Status ${response.status}: ${errorContextMessage}`,
      code,
      response.status
    );
  }

  return (await response.json()) as TResponse;
}
