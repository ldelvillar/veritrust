'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Result from '@/components/Result';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import { useAuth } from '@clerk/nextjs';
import { CONFIG } from '@/config';

interface AnalisisResult {
  analysis_id?: string | null;
  label: string;
  confidence: string;
  explanation: string;
}

type SourceType = 'text' | 'file' | 'url';

const isSourceType = (value: string | null): value is SourceType => {
  return value === 'text' || value === 'file' || value === 'url';
};

export default function AnalisisPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [result, setResult] = useState<AnalisisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const hasFetched = useRef(false);

  useEffect(() => {
    if (loading) document.title = 'Analizando el texto | VeriTrust';
    else document.title = 'Resultados del Análisis | VeriTrust';
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        'Resultados detallados del análisis del texto médico, incluyendo veredicto global, confianza y explicación.'
      );
  }, [loading]);

  useEffect(() => {
    if (hasFetched.current) return;
    hasFetched.current = true;

    const text = sessionStorage.getItem('analisis_text');
    const url = sessionStorage.getItem('analisis_url');
    const storedSourceType = sessionStorage.getItem('analisis_source_type');

    if (!text && !url) {
      router.replace('/');
      return;
    }

    const sourceType: SourceType = isSourceType(storedSourceType)
      ? storedSourceType
      : url
        ? 'url'
        : 'text';

    const requestBody =
      sourceType === 'url' && url
        ? { url, source_type: 'url' as const }
        : {
            text: text ?? '',
            source_type: sourceType === 'file' ? 'file' : 'text',
          };

    sessionStorage.removeItem('analisis_text');
    sessionStorage.removeItem('analisis_url');
    sessionStorage.removeItem('analisis_source_type');

    const fetchResult = async () => {
      try {
        const URL = CONFIG.API_URL + '/analisis';
        const token = await getToken();

        const response = await fetch(URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage =
            typeof errorData.detail === 'string'
              ? errorData.detail
              : Array.isArray(errorData.detail)
                ? errorData.detail[0].msg
                : `Status ${response.status}: Error al conectar con el servidor`;
          throw new Error(errorMessage);
        }

        const data = await response.json();

        if (typeof data.analysis_id === 'string' && data.analysis_id) {
          router.replace(`/analisis/${data.analysis_id}`);
          return;
        }

        setResult(data);
      } catch (err) {
        if (err instanceof Error) setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [router, getToken]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-12">
      {loading && (
        <div className="flex flex-col items-center gap-4 text-gray-500">
          <Spinner className="size-10 animate-spin text-primary" />
          <p className="text-lg font-medium">Analizando el texto...</p>
        </div>
      )}

      {error && (
        <div className="flex w-full max-w-2xl flex-col items-center gap-5 rounded-2xl border border-red-100 bg-white p-8 text-center shadow-2xl shadow-red-100/50 md:p-12">
          <div className="flex size-16 items-center justify-center rounded-full bg-red-100 text-red-500">
            <WarningIcon className="size-8" />
          </div>
          <div>
            <h2 className="mb-2 text-2xl font-bold text-gray-800">
              Ups, ha ocurrido un error
            </h2>
            <p className="text-base text-gray-600">{error}</p>
          </div>
          <button
            onClick={() => router.replace('/')}
            className="mt-3 rounded-xl bg-red-50 px-6 py-3 font-semibold text-red-600 transition-colors hover:bg-red-100 focus:ring-4 focus:ring-red-100 focus:outline-none"
          >
            Volver al inicio
          </button>
        </div>
      )}

      {result && <Result result={result} />}
    </div>
  );
}
