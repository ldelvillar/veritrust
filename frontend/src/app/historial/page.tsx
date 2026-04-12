'use client';

import { useAuth } from '@clerk/nextjs';
import { useCallback, useEffect, useMemo, useState } from 'react';
import HistoryFilters, {
  DateRangeFilter,
  ScoreSortOrder,
  SourceTypeFilter,
} from '@/components/HistoryFilters';
import HistoryResultsTable, {
  HistoryItem,
} from '@/components/HistoryResultsTable';
import { CONFIG } from '@/config';

const getScore = (confidence: number | string): number => {
  const parsed = Number(confidence);
  if (Number.isNaN(parsed)) return 0;

  const normalized = parsed <= 1 ? parsed * 100 : parsed;
  return Math.max(0, Math.min(100, Math.round(normalized)));
};

const getDateRangeThreshold = (
  dateRangeFilter: DateRangeFilter
): number | null => {
  const dayInMs = 24 * 60 * 60 * 1000;
  const now = Date.now();

  if (dateRangeFilter === '7d') return now - 7 * dayInMs;
  if (dateRangeFilter === '30d') return now - 30 * dayInMs;
  if (dateRangeFilter === '90d') return now - 90 * dayInMs;
  return null;
};

const matchesSearchQuery = (item: HistoryItem, query: string): boolean => {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery) return true;

  const searchableFields = [
    item.input_text,
    item.input_url,
    item.label,
    item.source_type,
  ];

  return searchableFields.some(field =>
    (field ?? '').toLocaleLowerCase().includes(normalizedQuery)
  );
};

export default function HistorialPage() {
  const { getToken } = useAuth();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceTypeFilter, setSourceTypeFilter] =
    useState<SourceTypeFilter>('all');
  const [dateRangeFilter, setDateRangeFilter] =
    useState<DateRangeFilter>('all');
  const [scoreSortOrder, setScoreSortOrder] = useState<ScoreSortOrder>('desc');

  const filteredHistory = useMemo(() => {
    const threshold = getDateRangeThreshold(dateRangeFilter);

    return history.filter(item => {
      const searchMatches = matchesSearchQuery(item, searchQuery);
      if (!searchMatches) return false;

      const sourceMatches =
        sourceTypeFilter === 'all' || item.source_type === sourceTypeFilter;
      if (!sourceMatches) return false;

      if (threshold === null) return true;

      const parsedDate = Date.parse(item.created_at);
      if (Number.isNaN(parsedDate)) return true;

      return parsedDate >= threshold;
    });
  }, [history, searchQuery, sourceTypeFilter, dateRangeFilter]);

  const sortedHistory = useMemo(() => {
    const sorted = [...filteredHistory];

    sorted.sort((a, b) => {
      const aScore = getScore(a.confidence);
      const bScore = getScore(b.confidence);

      return scoreSortOrder === 'desc' ? bScore - aScore : aScore - bScore;
    });

    return sorted;
  }, [filteredHistory, scoreSortOrder]);

  useEffect(() => {
    document.title = 'Historial de Análisis | VeriTrust';
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        'Revisa tu historial de análisis realizados en VeriTrust, con detalles de cada análisis y resultados obtenidos.'
      );
  }, []);

  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);

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
      setTotalCount(typeof data.count === 'number' ? data.count : items.length);
    } catch (error) {
      console.error('Error al obtener el historial de análisis:', error);

      setHistory([]);
      setTotalCount(0);
      setFetchError('Ha habido un error de comunicación con el servidor.');
    } finally {
      setIsLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    void fetchHistory();
  }, [fetchHistory]);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black tracking-tight text-slate-900">
            Análisis anteriores
          </h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Revisa y gestiona tus informes previos.
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

      <HistoryFilters
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        sourceTypeFilter={sourceTypeFilter}
        onSourceTypeFilterChange={setSourceTypeFilter}
        dateRangeFilter={dateRangeFilter}
        onDateRangeFilterChange={setDateRangeFilter}
        scoreSortOrder={scoreSortOrder}
        onScoreSortOrderChange={setScoreSortOrder}
      />

      <HistoryResultsTable
        history={sortedHistory}
        totalCount={totalCount}
        isLoading={isLoading}
        errorMessage={fetchError}
        onRetry={fetchHistory}
      />
    </section>
  );
}
