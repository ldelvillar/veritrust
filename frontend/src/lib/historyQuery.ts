import type { paths } from '@/types/api';

type HistoryParams = NonNullable<
  paths['/history']['get']['parameters']['query']
>;
type ExportParams = NonNullable<
  paths['/history/export']['get']['parameters']['query']
>;

export type SourceTypeFilter = NonNullable<HistoryParams['source_type']>;
export type VerdictFilter = NonNullable<HistoryParams['verdict']>;
export type StatusFilter = NonNullable<HistoryParams['status']>;
export type DateRangeFilter = NonNullable<HistoryParams['date_range']>;
export type SortOrder = NonNullable<HistoryParams['sort']>;

export interface HistoryFilters {
  search: string;
  sourceType: SourceTypeFilter;
  verdict: VerdictFilter;
  status: StatusFilter;
  dateRange: DateRangeFilter;
  sort: SortOrder;
}

export const PAGE_SIZE = 10;

export const DEFAULT_HISTORY_FILTERS: HistoryFilters = {
  search: '',
  sourceType: 'all',
  verdict: 'all',
  status: 'all',
  dateRange: 'all',
  sort: 'recent',
};

// Cada valor del contrato una vez: satisfies falla si el backend añade o quita uno.
const SOURCE_TYPES = {
  all: true,
  text: true,
  file: true,
  url: true,
} satisfies Record<SourceTypeFilter, true>;
const VERDICTS = {
  all: true,
  real: true,
  fake: true,
  uncertain: true,
} satisfies Record<VerdictFilter, true>;
const STATUSES = {
  all: true,
  pending: true,
  done: true,
  failed: true,
} satisfies Record<StatusFilter, true>;
const DATE_RANGES = {
  all: true,
  '7d': true,
  '30d': true,
  '90d': true,
} satisfies Record<DateRangeFilter, true>;
const SORTS = {
  recent: true,
  oldest: true,
  credibility_high: true,
  credibility_low: true,
} satisfies Record<SortOrder, true>;

type ParamReader = Pick<URLSearchParams, 'get'>;

function parseParam<T extends string>(
  value: string | null,
  allowed: Record<T, true>,
  fallback: T
): T {
  return value !== null && Object.hasOwn(allowed, value)
    ? (value as T)
    : fallback;
}

// Un valor fuera del contrato en la URL cae al de por defecto en vez de llegar al backend.
export function parseHistoryFilters(params: ParamReader): HistoryFilters {
  const defaults = DEFAULT_HISTORY_FILTERS;
  return {
    search: (params.get('search') ?? '').trim(),
    sourceType: parseParam(
      params.get('source_type'),
      SOURCE_TYPES,
      defaults.sourceType
    ),
    verdict: parseParam(params.get('verdict'), VERDICTS, defaults.verdict),
    status: parseParam(params.get('status'), STATUSES, defaults.status),
    dateRange: parseParam(
      params.get('date_range'),
      DATE_RANGES,
      defaults.dateRange
    ),
    sort: parseParam(params.get('sort'), SORTS, defaults.sort),
  };
}

export function parseHistoryPage(params: ParamReader): number {
  const page = Number.parseInt(params.get('page') ?? '1', 10);
  return Number.isFinite(page) && page > 0 ? page : 1;
}

function withSearch(
  endpoint: string,
  query: Record<string, string | number>,
  search: string
): string {
  const params = new URLSearchParams(
    Object.entries(query).map(([key, value]) => [key, String(value)])
  );
  if (search) params.set('search', search);
  return `${endpoint}?${params.toString()}`;
}

export function historyPath(filters: HistoryFilters, page: number): string {
  const query: Required<Omit<HistoryParams, 'search'>> = {
    page,
    page_size: PAGE_SIZE,
    source_type: filters.sourceType,
    verdict: filters.verdict,
    status: filters.status,
    date_range: filters.dateRange,
    sort: filters.sort,
  };
  return withSearch('/history', query, filters.search);
}

export function historyExportPath(filters: HistoryFilters): string {
  const query: Required<Omit<ExportParams, 'search'>> = {
    source_type: filters.sourceType,
    verdict: filters.verdict,
    status: filters.status,
    date_range: filters.dateRange,
    sort: filters.sort,
  };
  return withSearch('/history/export', query, filters.search);
}

// Solo se exportan análisis completados: con «En curso» o «Fallido» no hay nada que exportar.
export function isExportable(status: StatusFilter): boolean {
  return status === 'all' || status === 'done';
}

// Consulta que precarga el servidor; el cliente solo reusa initialData si su ruta coincide.
export const INITIAL_HISTORY_PATH = historyPath(DEFAULT_HISTORY_FILTERS, 1);
