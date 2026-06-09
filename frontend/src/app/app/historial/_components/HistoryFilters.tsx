import Chevron from '@/assets/Chevron';
import Magnifier from '@/assets/Magnifier';

export type DateSortOrder = 'desc' | 'asc';
export type DateRangeFilter = 'all' | '7d' | '30d' | '90d';
export type SourceTypeFilter = 'all' | 'text' | 'file' | 'url';
export type VerdictFilter = 'all' | 'real' | 'fake' | 'uncertain';

interface HistoryFiltersProps {
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  sourceTypeFilter: SourceTypeFilter;
  onSourceTypeFilterChange: (value: SourceTypeFilter) => void;
  verdictFilter: VerdictFilter;
  onVerdictFilterChange: (value: VerdictFilter) => void;
  dateRangeFilter: DateRangeFilter;
  onDateRangeFilterChange: (value: DateRangeFilter) => void;
  dateSortOrder: DateSortOrder;
  onDateSortOrderChange: (value: DateSortOrder) => void;
}

export default function HistoryFilters({
  searchQuery,
  onSearchQueryChange,
  sourceTypeFilter,
  onSourceTypeFilterChange,
  verdictFilter,
  onVerdictFilterChange,
  dateRangeFilter,
  onDateRangeFilterChange,
  dateSortOrder,
  onDateSortOrderChange,
}: HistoryFiltersProps) {
  return (
    <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-[1fr_auto_auto_auto_auto]">
      <label className="relative block">
        <span className="sr-only">
          Buscar análisis por título o palabra clave
        </span>
        <Magnifier className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={event => onSearchQueryChange(event.target.value)}
          placeholder="Buscar artículos por título o palabra clave"
          className="h-11 w-full rounded-xl border border-border bg-white pl-10 text-sm text-slate-600 transition-all outline-none placeholder:text-slate-400 hover:border-primary/50 focus:border-primary focus:ring-2 focus:ring-primary/10"
        />
      </label>

      <label className="relative block">
        <select
          value={sourceTypeFilter}
          onChange={event =>
            onSourceTypeFilterChange(event.target.value as SourceTypeFilter)
          }
          className="h-11 w-full min-w-44 cursor-pointer appearance-none rounded-xl border border-border bg-white px-4 pr-10 text-sm font-medium text-slate-600 transition-all outline-none hover:border-primary/50 focus:border-primary focus:ring-2 focus:ring-primary/10"
        >
          <option value="all">Todos los tipos</option>
          <option value="text">Texto pegado</option>
          <option value="file">Carga de archivo</option>
          <option value="url">Enlace</option>
        </select>
        <div className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-slate-400">
          <Chevron />
        </div>
      </label>

      <label className="relative block">
        <select
          value={verdictFilter}
          onChange={event =>
            onVerdictFilterChange(event.target.value as VerdictFilter)
          }
          className="h-11 w-full min-w-44 cursor-pointer appearance-none rounded-xl border border-border bg-white px-4 pr-10 text-sm font-medium text-slate-600 transition-all outline-none hover:border-primary/50 focus:border-primary focus:ring-2 focus:ring-primary/10"
        >
          <option value="all">Todos los veredictos</option>
          <option value="real">Verdadera</option>
          <option value="fake">Falsa</option>
          <option value="uncertain">Incierta</option>
        </select>
        <div className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-slate-400">
          <Chevron />
        </div>
      </label>

      <label className="relative block">
        <select
          value={dateRangeFilter}
          onChange={event =>
            onDateRangeFilterChange(event.target.value as DateRangeFilter)
          }
          className="h-11 w-full min-w-48 cursor-pointer appearance-none rounded-xl border border-border bg-white px-4 pr-10 text-sm font-medium text-slate-600 transition-all outline-none hover:border-primary/50 focus:border-primary focus:ring-2 focus:ring-primary/10"
        >
          <option value="all">Rango de fechas: todas</option>
          <option value="7d">Últimos 7 días</option>
          <option value="30d">Últimos 30 días</option>
          <option value="90d">Últimos 90 días</option>
        </select>
        <div className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-slate-400">
          <Chevron />
        </div>
      </label>

      <label className="relative block">
        <select
          value={dateSortOrder}
          onChange={event =>
            onDateSortOrderChange(event.target.value as DateSortOrder)
          }
          className="h-11 w-full min-w-56 cursor-pointer appearance-none rounded-xl border border-border bg-white px-4 pr-10 text-sm font-medium text-slate-600 transition-all outline-none hover:border-primary/50 focus:border-primary focus:ring-2 focus:ring-primary/10"
        >
          <option value="desc">Más recientes primero</option>
          <option value="asc">Más antiguos primero</option>
        </select>
        <div className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-slate-400">
          <Chevron />
        </div>
      </label>
    </div>
  );
}
