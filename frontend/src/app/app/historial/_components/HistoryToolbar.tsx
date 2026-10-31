import CalendarIcon from '@/assets/Calendar';
import CrossIcon from '@/assets/Cross';
import FunnelIcon from '@/assets/Funnel';
import Magnifier from '@/assets/Magnifier';
import SortIcon from '@/assets/Sort';
import { STATUS_LABEL } from '@/components/analysis-result/format';
import type {
  DateRangeFilter,
  SortOrder,
  SourceTypeFilter,
  StatusFilter,
} from '@/lib/historyQuery';
import FilterSelect from './FilterSelect';

const SOURCE_TYPE_OPTIONS = [
  { value: 'all' as SourceTypeFilter, label: 'Todos los tipos' },
  { value: 'text' as SourceTypeFilter, label: 'Texto' },
  { value: 'url' as SourceTypeFilter, label: 'Enlace' },
  { value: 'file' as SourceTypeFilter, label: 'Archivo' },
];

const STATUS_OPTIONS = [
  { value: 'all' as StatusFilter, label: 'Todos los estados' },
  { value: 'done' as StatusFilter, label: STATUS_LABEL.done },
  { value: 'pending' as StatusFilter, label: STATUS_LABEL.pending },
  { value: 'failed' as StatusFilter, label: STATUS_LABEL.failed },
];

const DATE_RANGE_OPTIONS = [
  { value: 'all' as DateRangeFilter, label: 'Todo el periodo' },
  { value: '7d' as DateRangeFilter, label: 'Últimos 7 días' },
  { value: '30d' as DateRangeFilter, label: 'Últimos 30 días' },
  { value: '90d' as DateRangeFilter, label: 'Últimos 90 días' },
];

const SORT_OPTIONS = [
  { value: 'recent' as SortOrder, label: 'Más recientes' },
  { value: 'oldest' as SortOrder, label: 'Más antiguos' },
  { value: 'credibility_high' as SortOrder, label: 'Mayor credibilidad' },
  { value: 'credibility_low' as SortOrder, label: 'Menor credibilidad' },
];

interface HistoryToolbarProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  sourceTypeFilter: SourceTypeFilter;
  onSourceTypeChange: (value: SourceTypeFilter) => void;
  statusFilter: StatusFilter;
  onStatusChange: (value: StatusFilter) => void;
  dateRangeFilter: DateRangeFilter;
  onDateRangeChange: (value: DateRangeFilter) => void;
  sortOrder: SortOrder;
  onSortChange: (value: SortOrder) => void;
  disabled?: boolean;
}

// History search and filters, whose state lives in useHistoryFilters (the URL).
export default function HistoryToolbar({
  searchQuery,
  onSearchChange,
  sourceTypeFilter,
  onSourceTypeChange,
  statusFilter,
  onStatusChange,
  dateRangeFilter,
  onDateRangeChange,
  sortOrder,
  onSortChange,
  disabled = false,
}: HistoryToolbarProps) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2.5 md:gap-3">
      <label
        className={`relative flex h-11.5 min-w-0 flex-[1_1_100%] items-center gap-2.75 rounded-xl border border-line-strong bg-white px-3.5 text-faint transition focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/10 md:min-w-55 md:flex-1 ${disabled ? 'opacity-50' : ''}`}
      >
        <Magnifier className="size-4.5 shrink-0 text-faint" aria-hidden />
        <input
          type="text"
          value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          disabled={disabled}
          placeholder="Buscar por título o fuente…"
          className="min-w-0 flex-1 border-none bg-transparent text-sm text-ink outline-none placeholder:text-faint disabled:cursor-not-allowed"
        />
        {searchQuery ? (
          <button
            type="button"
            onClick={() => onSearchChange('')}
            aria-label="Limpiar búsqueda"
            className="grid size-6 shrink-0 place-items-center rounded-lg transition hover:bg-primary/8 hover:text-body"
          >
            <CrossIcon className="size-3.75" />
          </button>
        ) : null}
      </label>

      <FilterSelect
        value={sourceTypeFilter}
        onChange={onSourceTypeChange}
        options={SOURCE_TYPE_OPTIONS}
        icon={<FunnelIcon className="size-4" aria-hidden />}
        ariaLabel="Filtrar por tipo"
        className="flex-[1_1_100%] sm:flex-none"
        disabled={disabled}
      />

      <FilterSelect
        value={statusFilter}
        onChange={onStatusChange}
        options={STATUS_OPTIONS}
        icon={<FunnelIcon className="size-4" aria-hidden />}
        ariaLabel="Filtrar por estado"
        className="flex-[1_1_100%] sm:flex-none"
        disabled={disabled}
      />

      <FilterSelect
        value={dateRangeFilter}
        onChange={onDateRangeChange}
        options={DATE_RANGE_OPTIONS}
        icon={<CalendarIcon className="size-4" aria-hidden />}
        ariaLabel="Filtrar por rango de fechas"
        className="flex-[1_1_100%] sm:flex-none"
        disabled={disabled}
      />

      <FilterSelect
        value={sortOrder}
        onChange={onSortChange}
        options={SORT_OPTIONS}
        icon={<SortIcon className="size-4" aria-hidden />}
        ariaLabel="Ordenar"
        className="flex-[1_1_100%] sm:flex-none"
        disabled={disabled}
      />
    </div>
  );
}
