'use client';

import { useAuth } from '@clerk/nextjs';
import { useEffect, useState } from 'react';
import HistoryFilters from '@/components/HistoryFilters';
import HistoryResultsTable, {
  HistoryItem,
} from '@/components/HistoryResultsTable';
import { CONFIG } from '@/config';

export default function HistorialPage() {
  const { getToken } = useAuth();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    document.title = 'Historial de Análisis | VeriTrust';
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        'Revisa tu historial de análisis realizados en VeriTrust, con detalles de cada análisis y resultados obtenidos.'
      );
  }, []);

  useEffect(() => {
    const fetchHistory = async () => {
      setIsLoading(true);

      try {
        const URL = CONFIG.API_URL + '/historial';
        const token = await getToken();

        if (!token) {
          throw new Error('No se pudo obtener el token de autenticación.');
        }

        const response = await fetch(URL, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
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
        const items = Array.isArray(data.items) ? data.items : [];
        setHistory(items);
        setTotalCount(
          typeof data.count === 'number' ? data.count : items.length
        );
      } catch (error) {
        console.error('Error al obtener el historial de análisis:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHistory();
  }, [getToken]);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black tracking-tight text-slate-900">
            Análisis anteriores
          </h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Revisa y gestiona tus informes previos de credibilidad de noticias.
          </p>
        </div>

        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-primary/8 px-4 py-2 text-sm font-bold text-primary"
        >
          <span aria-hidden>↓</span>
          Exportar todo
        </button>
      </div>

      <HistoryFilters />

      <HistoryResultsTable
        history={history}
        totalCount={totalCount}
        isLoading={isLoading}
      />
    </section>
  );
}
