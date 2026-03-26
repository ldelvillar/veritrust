'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Spinner from '@/assets/Spinner';
import Result from '@/components/Result';

interface AnalisisResult {
  label: string;
  confidence: string;
  explanation: string;
}

export default function AnalisisPage() {
  const router = useRouter();
  const [result, setResult] = useState<AnalisisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const hasFetched = useRef(false);

  useEffect(() => {
    if (hasFetched.current) return;
    hasFetched.current = true;

    const text = sessionStorage.getItem('analisis_text');

    if (!text) {
      router.replace('/');
      return;
    }

    sessionStorage.removeItem('analisis_text');

    const fetchResult = async () => {
      try {
        const URL = 'http://127.0.0.1:8000/analisis';
        const response = await fetch(URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text }),
        });

        if (!response.ok)
          throw new Error(`Response status: ${response.status}`);

        const data = await response.json();
        setResult(data);
      } catch (err) {
        if (err instanceof Error) setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [router]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-12">
      {loading && (
        <div className="flex flex-col items-center gap-4 text-gray-500">
          <Spinner className="size-10 animate-spin text-primary" />
          <p className="text-lg font-medium">Analizando el texto...</p>
        </div>
      )}

      {error && (
        <div className="w-full max-w-3xl rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
          <p className="font-semibold">Error al procesar el análisis</p>
          <p className="mt-1 text-sm">{error}</p>
        </div>
      )}

      {result && <Result result={result} />}
    </div>
  );
}
