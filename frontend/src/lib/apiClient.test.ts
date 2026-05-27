import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  buildApiUrl,
  fetchJsonWithAuth,
  parseErrorDetail,
} from './apiClient';

describe('buildApiUrl', () => {
  it('passes through absolute http(s) URLs unchanged', () => {
    expect(buildApiUrl('https://example.com/x')).toBe('https://example.com/x');
    expect(buildApiUrl('http://example.com/x')).toBe('http://example.com/x');
  });

  it('prefixes relative paths with the configured API base', () => {
    // CONFIG.API_URL falls back to http://127.0.0.1:8000 when the env var is unset.
    expect(buildApiUrl('/analysis')).toBe('http://127.0.0.1:8000/analysis');
  });

  it('adds a leading slash when the path is missing one', () => {
    expect(buildApiUrl('analysis')).toBe('http://127.0.0.1:8000/analysis');
  });
});

describe('parseErrorDetail', () => {
  it('extracts the structured {code, message} contract', () => {
    expect(
      parseErrorDetail({ code: 'NO_MEDICAL_CLAIMS', message: 'Sin afirmaciones' })
    ).toEqual({ code: 'NO_MEDICAL_CLAIMS', message: 'Sin afirmaciones' });
  });

  it('keeps a code even when the message is absent', () => {
    expect(parseErrorDetail({ code: 'INTERNAL' })).toEqual({
      code: 'INTERNAL',
      message: null,
    });
  });

  it('treats a plain string detail as a message with no code', () => {
    expect(parseErrorDetail('Token expired')).toEqual({
      message: 'Token expired',
      code: null,
    });
  });

  it('extracts the first msg from a FastAPI 422 validation array', () => {
    const detail = [
      { loc: ['body', 'url'], msg: 'field required', type: 'value_error' },
    ];
    expect(parseErrorDetail(detail)).toEqual({
      message: 'field required',
      code: null,
    });
  });

  it('returns nulls for unrecognised shapes', () => {
    expect(parseErrorDetail(null)).toEqual({ message: null, code: null });
    expect(parseErrorDetail({})).toEqual({ message: null, code: null });
    expect(parseErrorDetail([])).toEqual({ message: null, code: null });
    expect(parseErrorDetail(42)).toEqual({ message: null, code: null });
  });
});

describe('fetchJsonWithAuth', () => {
  const getToken = vi.fn(async (): Promise<string | null> => 'jwt-123');

  beforeEach(() => {
    getToken.mockClear();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const mockFetch = () => vi.mocked(fetch);

  it('throws when no auth token is available', async () => {
    getToken.mockResolvedValueOnce(null);
    await expect(
      fetchJsonWithAuth(getToken, '/dashboard/summary', { method: 'GET' })
    ).rejects.toThrow('No se pudo obtener el token de autenticación.');
    expect(mockFetch()).not.toHaveBeenCalled();
  });

  it('attaches the bearer token and JSON content-type for a body', async () => {
    mockFetch().mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await fetchJsonWithAuth(getToken, '/analysis', {
      method: 'POST',
      body: { url: 'https://x.test', source_type: 'url' },
    });

    expect(getToken).toHaveBeenCalledWith({ template: 'veritrust-api' });
    const [, init] = mockFetch().mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get('Authorization')).toBe('Bearer jwt-123');
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(init?.body).toBe(
      JSON.stringify({ url: 'https://x.test', source_type: 'url' })
    );
  });

  it('returns parsed JSON on a 2xx response', async () => {
    mockFetch().mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'ready' }), { status: 200 })
    );

    const data = await fetchJsonWithAuth<{ status: string }>(
      getToken,
      '/healthz',
      { method: 'GET' }
    );
    expect(data).toEqual({ status: 'ready' });
  });

  it('throws an ApiError carrying the structured code and status on failure', async () => {
    mockFetch().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: { code: 'SERVICE_UNAVAILABLE', message: 'No disponible' },
        }),
        { status: 503 }
      )
    );

    const error = (await fetchJsonWithAuth(getToken, '/analysis', {
      method: 'POST',
      body: { text: 'x' },
    }).catch(e => e)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe('SERVICE_UNAVAILABLE');
    expect(error.message).toBe('No disponible');
    expect(error.status).toBe(503);
  });

  it('falls back to a generic message when the error body is not JSON', async () => {
    mockFetch().mockResolvedValueOnce(new Response('boom', { status: 500 }));

    const error = (await fetchJsonWithAuth(getToken, '/healthz', {
      method: 'GET',
    }).catch(e => e)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBeNull();
    expect(error.status).toBe(500);
  });
});
