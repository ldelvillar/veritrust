import Magnifier from '@/assets/Magnifier';

export type ScoreSortOrder = 'desc' | 'asc';
export type DateRangeFilter = 'all' | '7d' | '30d' | '90d';
export type SourceTypeFilter = 'all' | 'text' | 'file' | 'url';

interface HistoryFiltersProps {
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  sourceTypeFilter: SourceTypeFilter;
  onSourceTypeFilterChange: (value: SourceTypeFilter) => void;
  dateRangeFilter: DateRangeFilter;
  onDateRangeFilterChange: (value: DateRangeFilter) => void;
  scoreSortOrder: ScoreSortOrder;
  onScoreSortOrderChange: (value: ScoreSortOrder) => void;
}

export default function HistoryFilters({
  searchQuery,
  onSearchQueryChange,
  sourceTypeFilter,
  onSourceTypeFilterChange,
  dateRangeFilter,
  onDateRangeFilterChange,
  scoreSortOrder,
  onScoreSortOrderChange,
}: HistoryFiltersProps) {
  return (
    <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
      <label className="relative block">
        <Magnifier className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={event => onSearchQueryChange(event.target.value)}
          placeholder="Buscar artículos por título o palabra clave"
          className="h-11 w-full rounded-xl border border-border bg-white pl-10 text-sm text-slate-500 outline-none"
        />
      </label>

      <label className="relative block">
        <select
          value={sourceTypeFilter}
          onChange={event =>
            onSourceTypeFilterChange(event.target.value as SourceTypeFilter)
          }
          className="h-11 w-full min-w-44 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-slate-600 outline-none"
        >
          <option value="all">Todos los tipos</option>
          <option value="text">Texto pegado</option>
          <option value="file">Carga de archivo</option>
          <option value="url">Enlace</option>
        </select>
      </label>

      <label className="relative block">
        <select
          value={dateRangeFilter}
          onChange={event =>
            onDateRangeFilterChange(event.target.value as DateRangeFilter)
          }
          className="h-11 w-full min-w-48 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-slate-600 outline-none"
        >
          <option value="all">Rango de fechas: todas</option>
          <option value="7d">Últimos 7 días</option>
          <option value="30d">Últimos 30 días</option>
          <option value="90d">Últimos 90 días</option>
        </select>
      </label>

      <label className="relative block">
        <select
          value={scoreSortOrder}
          onChange={event =>
            onScoreSortOrderChange(event.target.value as ScoreSortOrder)
          }
          className="h-11 w-full min-w-56 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-slate-600 outline-none"
        >
          <option value="desc">Puntuación: mayor a menor</option>
          <option value="asc">Puntuación: menor a mayor</option>
        </select>
      </label>
    </div>
  );
}
